"""Create a local DEMO database from the synthetic fixture.

    QMS_MODE=demo python -m qms_os.seed            # fresh database with the synthetic org only
    QMS_MODE=demo python -m qms_os.seed --demo     # plus a drafted/approved synthetic 2026 programme

Refuses to run unless QMS_MODE is demo or test: it creates a fictional organisation and must never
be mixed with an operational database.
"""
from __future__ import annotations

import argparse
from datetime import date

from .db import Base, create_all, make_engine, make_sessionmaker
from .fixtures import load
from .knowledge.store import KnowledgeBase
from .policy import PolicyConfigError, load_context
from .services import program as PS


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="also draft and approve a synthetic 2026 audit programme")
    args = ap.parse_args()
    ctx = load_context()
    if not ctx.synthetic:
        raise PolicyConfigError("the seed creates a synthetic organisation; set QMS_MODE=demo to use it")
    engine = make_engine()
    Base.metadata.drop_all(engine)
    KnowledgeBase.metadata.drop_all(engine)
    create_all(engine)
    with make_sessionmaker(engine)() as s:
        users = load(s)
        if args.demo:
            prog = PS.create_program(s, users["ma"], 2026, ctx, date.today())
            PS.approve_program(s, users["ma"], prog.id, ctx, date.today())
        s.commit()
    print(f"Seeded {engine.url} ({ctx.mode} mode, synthetic organisation)")


if __name__ == "__main__":
    main()
