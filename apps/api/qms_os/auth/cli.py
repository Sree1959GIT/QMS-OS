"""Local administration commands (run on the host by the operator).

    python -m qms_os.auth generate-key --out PATH        # new AES-GCM key file; never overwrites
    python -m qms_os.auth bootstrap-admin --email E --name N
    python -m qms_os.auth grant-account-admin EMAIL      # asks you to type the e-mail address again
    python -m qms_os.auth revoke-account-admin EMAIL

``bootstrap-admin`` creates the first account admin. It runs only while no active account admin exists, asks for
the password interactively (never from arguments or the environment), requires a confirming authenticator code, and
prints the recovery codes once. It needs QMS_AUTH_KEY_FILE and the database named by QMS_DATABASE_URL.

``grant-account-admin`` and ``revoke-account-admin`` change the ``account_admin`` platform role of a person with an
active account; there is no API route for this. Revoking the last active account admin is refused. Each change writes
an audit event (actor kind "operator", channel "cli"). They need only the database named by QMS_DATABASE_URL.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from typing import Callable

from ..db import make_engine, make_sessionmaker, prepare_schema
from ..services.common import AuthFailure, RuleViolation
from .keys import KEY_ENV, SecretBox, generate_key_file, load_key_file
from .limits import AuthConfigError
from .service import AuthContext, bootstrap_admin, find_user, grant_account_admin, revoke_account_admin


def run_bootstrap(maker, ctx: AuthContext, email: str, name: str, *, read_secret: Callable[[str], str],
                  read_line: Callable[[str], str], write: Callable[[str], None]) -> int:
    password = read_secret("New password: ")
    if read_secret("Repeat password: ") != password:
        write("The passwords do not match; nothing was changed.")
        return 1

    def confirm(setup: dict) -> str:
        write("Add this account to an authenticator app, then enter the current code.")
        write(f"  set-up link: {setup['otpauth_uri']}")
        write(f"  or key:      {setup['secret']}")
        return read_line("Authenticator code: ")

    with maker() as s:
        s.info["actor_kind"], s.info["channel"] = "human", "cli"
        try:
            user, codes = bootstrap_admin(s, ctx, email=email, name=name, password=password, confirm_code=confirm)
        except (RuleViolation, AuthFailure) as e:
            s.rollback()
            write(f"Refused: {e}")
            return 1
        s.commit()
    write(f"Account admin created for {user.email}. Recovery codes (shown once; store them offline):")
    for c in codes:
        write(f"  {c}")
    return 0


def run_grant(maker, email: str, *, read_line: Callable[[str], str], write: Callable[[str], None]) -> int:
    """Grant account_admin after the operator types the e-mail address a second time."""
    with maker() as s:
        person = find_user(s, email)
        if person is not None:
            typed = read_line(f"Grant the account_admin role to {person.email}? Type the e-mail address again to "
                              "confirm: ")
            if typed.strip().lower() != person.email.lower():
                write("The e-mail address did not match; nothing was changed.")
                return 1
        try:
            user = grant_account_admin(s, email)
        except RuleViolation as e:
            s.rollback()
            write(f"Refused: {e}")
            return 1
        s.commit()
    write(f"{user.email} is now an account admin.")
    return 0


def run_revoke(maker, email: str, *, write: Callable[[str], None]) -> int:
    with maker() as s:
        try:
            user = revoke_account_admin(s, email)
        except RuleViolation as e:
            s.rollback()
            write(f"Refused: {e}")
            return 1
        s.commit()
    write(f"{user.email} is no longer an account admin.")
    return 0


def _database():
    engine = make_engine()
    prepare_schema(engine)
    return make_sessionmaker(engine)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m qms_os.auth")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate-key", help="write a new authentication key file (never overwrites)")
    g.add_argument("--out", required=True)
    b = sub.add_parser("bootstrap-admin", help="create the first account admin")
    b.add_argument("--email", required=True)
    b.add_argument("--name", required=True)
    gr = sub.add_parser("grant-account-admin", help="give a person with an active account the account_admin role")
    gr.add_argument("email")
    rv = sub.add_parser("revoke-account-admin", help="remove the account_admin role (never the last active one)")
    rv.add_argument("email")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "generate-key":
            path = generate_key_file(args.out)
            print(f"Key written to {path}. Keep it outside Git and back it up separately from the database.")
            return 0
        if args.cmd == "grant-account-admin":
            return run_grant(_database(), args.email, read_line=input, write=print)
        if args.cmd == "revoke-account-admin":
            return run_revoke(_database(), args.email, write=print)
        key_file = os.environ.get(KEY_ENV)
        if not key_file:
            raise AuthConfigError(f"set {KEY_ENV} to the authentication key file")
        ctx = AuthContext(box=SecretBox(load_key_file(key_file)))
        return run_bootstrap(_database(), ctx, args.email, args.name, read_secret=getpass.getpass,
                             read_line=input, write=print)
    except AuthConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
