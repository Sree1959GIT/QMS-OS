"""python -m qms_os.evidence COMMAND  (synthetic fixtures only; R-34, R-50, R-54)

  init-store DIR      create the interim evidence store folder and its marker file (outside any Git work tree)
  put FILE --mime M --owner-email E --classification C --synthetic
                      store one synthetic file; needs QMS_EVIDENCE_DIR and QMS_DATABASE_URL

Both refuse operational mode (QMS_MODE must be demo or test). Each stored object writes an audit event (actor kind
"operator", channel "cli"). There is no command to overwrite or delete an object (R-52).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import func, select

from ..db import make_engine, make_sessionmaker, prepare_schema
from ..models import User
from ..policy import load_context
from ..services.common import ServiceError
from .contract import MIME_TYPES, StoreRefused
from .local import EVIDENCE_ENV, LocalContentStore, init_store
from .service import store_object


def main(argv: list[str] | None = None, env=None) -> int:
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser(prog="python -m qms_os.evidence")
    sub = ap.add_subparsers(dest="cmd", required=True)
    init = sub.add_parser("init-store", help="create the store folder and its marker file")
    init.add_argument("folder")
    put = sub.add_parser("put", help="store one synthetic file")
    put.add_argument("file")
    put.add_argument("--mime", required=True, choices=MIME_TYPES)
    put.add_argument("--owner-email", required=True)
    put.add_argument("--classification", required=True)
    put.add_argument("--synthetic", action="store_true", help="required: the file is a synthetic fixture")
    args = ap.parse_args(argv)
    try:
        mode = load_context(env=env).mode.value
        if args.cmd == "init-store":
            print(f"created {init_store(args.folder, mode)}")
            return 0
        if not args.synthetic:
            raise StoreRefused("--synthetic is required: only synthetic fixtures may be stored (R-54)")
        folder = env.get(EVIDENCE_ENV, "").strip()
        if not folder:
            raise StoreRefused(f"set {EVIDENCE_ENV} to the evidence store folder")
        store = LocalContentStore(folder, qms_mode=mode)
        engine = make_engine(env.get("QMS_DATABASE_URL") or None)
        prepare_schema(engine)
        with make_sessionmaker(engine)() as s:
            s.info.update(actor_kind="operator", channel="cli")
            owner = s.scalar(select(User).where(func.lower(User.email) == args.owner_email.strip().lower()))
            if owner is None:
                raise StoreRefused("no person has that e-mail address")
            row, created = store_object(s, store, data=Path(args.file).read_bytes(), mime=args.mime,
                                        owner_id=owner.id, classification=args.classification, synthetic=True)
            s.commit()
            print(f"{'stored' if created else 'already stored'} {row.sha256}")
        return 0
    except (StoreRefused, ServiceError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
