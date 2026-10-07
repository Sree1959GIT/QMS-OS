"""Static checks on the Alembic migrations (no database or Alembic needed, so these run in CI).

Records are never deleted (docs/DECISIONS.md D-14): no migration drops a table or column or deletes rows, and every
downgrade() raises instead of undoing the schema. Upgrades are additive: they only create tables, keys and indexes or
add columns that existing rows can satisfy (nullable or with a server default).
"""
import ast
import re
from pathlib import Path

VERSIONS = Path(__file__).resolve().parents[1] / "migrations" / "versions"
DESTRUCTIVE_OPS = {"drop_table", "drop_column"}
ADDITIVE_OPS = {"create_table", "add_column", "create_foreign_key", "create_index", "create_unique_constraint"}
DESTRUCTIVE_SQL = re.compile(r"\b(drop\s+table|drop\s+schema|delete\s+from|truncate)\b", re.I)


def _migrations():
    files = sorted(VERSIONS.glob("*.py"))
    assert files, "no migrations found"
    return [(f.name, ast.parse(f.read_text(encoding="utf-8"))) for f in files]


def _assigned(tree, name):
    for node in tree.body:
        targets = (node.targets if isinstance(node, ast.Assign)
                   else [node.target] if isinstance(node, ast.AnnAssign) else [])
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not assigned")


def test_exactly_one_baseline_revision():
    assert len([n for n, tree in _migrations() if _assigned(tree, "down_revision") is None]) == 1


def test_every_downgrade_raises():
    for name, tree in _migrations():
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "downgrade")
        body = [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
        assert len(body) == 1 and isinstance(body[0], ast.Raise), f"{name}: downgrade() must only raise"


def test_no_migration_drops_tables_or_columns_or_deletes_rows():
    for name, tree in _migrations():
        calls = {getattr(c.func, "attr", getattr(c.func, "id", "")) for c in ast.walk(tree) if isinstance(c, ast.Call)}
        assert not calls & DESTRUCTIVE_OPS, f"{name}: {sorted(calls & DESTRUCTIVE_OPS)}"
        strings = [c.value for c in ast.walk(tree) if isinstance(c, ast.Constant) and isinstance(c.value, str)]
        assert not [s for s in strings if DESTRUCTIVE_SQL.search(s)], name


def test_upgrades_are_additive():
    for name, tree in _migrations():
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "upgrade")
        ops = [c for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
               and isinstance(c.func.value, ast.Name) and c.func.value.id == "op"]
        assert ops and {c.func.attr for c in ops} <= ADDITIVE_OPS, f"{name}: {sorted({c.func.attr for c in ops})}"
        for c in (c for c in ops if c.func.attr == "add_column"):
            col = c.args[1]
            kw = {k.arg: k.value for k in col.keywords}
            nullable = isinstance(kw.get("nullable"), ast.Constant) and kw["nullable"].value is True
            assert nullable or "server_default" in kw, f"{name}: add_column needs nullable=True or a server_default"
