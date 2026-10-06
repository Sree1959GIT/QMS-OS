"""Local administration commands (run on the host by the operator).

    python -m qms_os.auth generate-key --out PATH        # new AES-GCM key file; never overwrites
    python -m qms_os.auth bootstrap-admin --email E --name N

``bootstrap-admin`` creates the first account admin. It runs only while no active account admin exists, asks for
the password interactively (never from arguments or the environment), requires a confirming authenticator code, and
prints the recovery codes once. It needs QMS_AUTH_KEY_FILE and the database named by QMS_DATABASE_URL.
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
from .service import AuthContext, bootstrap_admin


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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m qms_os.auth")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate-key", help="write a new authentication key file (never overwrites)")
    g.add_argument("--out", required=True)
    b = sub.add_parser("bootstrap-admin", help="create the first account admin")
    b.add_argument("--email", required=True)
    b.add_argument("--name", required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "generate-key":
            path = generate_key_file(args.out)
            print(f"Key written to {path}. Keep it outside Git and back it up separately from the database.")
            return 0
        key_file = os.environ.get(KEY_ENV)
        if not key_file:
            raise AuthConfigError(f"set {KEY_ENV} to the authentication key file")
        ctx = AuthContext(box=SecretBox(load_key_file(key_file)))
        engine = make_engine()
        prepare_schema(engine)
        return run_bootstrap(make_sessionmaker(engine), ctx, args.email, args.name, read_secret=getpass.getpass,
                             read_line=input, write=print)
    except AuthConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
