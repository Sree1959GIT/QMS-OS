"""Static checks on the Alembic migrations (no database or Alembic needed, so these run in CI).

Records are never deleted (docs/DECISIONS.md D-14): no migration drops a table or column or deletes rows, and every
downgrade() raises instead of undoing the schema. Upgrades are additive: they only create tables, keys and indexes or
add columns that existing rows can satisfy (nullable or with a server default). The one raw-SQL exception is
``op.execute`` of a literal ``CREATE FUNCTION`` or ``CREATE TRIGGER`` statement whose name is in ``DB_OBJECTS`` (R-52,
R-63: the triggers that make evidence and workflow rows immutable); ``CREATE OR REPLACE``, any other statement, any
other name and any non-literal argument fail here. Function bodies are not inspected: a new name needs a reviewed
change to ``DB_OBJECTS``.
"""
import ast
import re
from pathlib import Path

VERSIONS = Path(__file__).resolve().parents[1] / "migrations" / "versions"
DESTRUCTIVE_OPS = {"drop_table", "drop_column"}
ADDITIVE_OPS = {"create_table", "add_column", "create_foreign_key", "create_index", "create_unique_constraint"}
EXECUTE_ALLOWED = re.compile(r"CREATE (FUNCTION|TRIGGER) ([a-z_]+)[ (]")
DB_OBJECTS = {                    # R-63: every function and trigger a migration may create, by name
    "evidence_objects_immutable",                                                       # R-52
    "workflow_rows_immutable", "workflow_version_frozen", "workflow_versions_no_delete",
    "workflow_approvals_immutable",                                                     # R-58
}
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


def _literal_string(node) -> str | None:
    """A string literal, or an implicit or ``+`` concatenation of string literals; otherwise None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _literal_string(node.left), _literal_string(node.right)
        return None if left is None or right is None else left + right
    return None


def _allowed(sql: str | None) -> bool:
    m = EXECUTE_ALLOWED.match(sql) if sql is not None else None
    return m is not None and m.group(2) in DB_OBJECTS


def test_execute_rule_accepts_only_literal_create_function_or_trigger_with_a_listed_name():
    def ok(src: str) -> bool:
        return _allowed(_literal_string(ast.parse(src).body[0].value.args[0]))
    assert ok('op.execute("CREATE TRIGGER workflow_version_frozen BEFORE UPDATE ON x FOR EACH ROW EXECUTE F()")')
    assert ok('op.execute("CREATE FUNCTION workflow_rows_immutable() RETURNS trigger " "LANGUAGE plpgsql AS $$ $$")')
    assert not ok('op.execute("CREATE TRIGGER t BEFORE UPDATE ON x FOR EACH ROW EXECUTE FUNCTION f()")')  # unlisted
    assert not ok('op.execute("CREATE FUNCTION workflow_rows_immutable_x() RETURNS trigger AS $$ $$")')
    assert not ok('op.execute("CREATE OR REPLACE FUNCTION f() RETURNS trigger AS $$ $$")')
    assert not ok('op.execute("ALTER TABLE x DROP CONSTRAINT y")')
    assert not ok('op.execute("UPDATE x SET y = 1")')
    assert not ok('op.execute(statement)')
    assert not ok('op.execute(f"CREATE TRIGGER {name}")')


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
        used = {c.func.attr for c in ops}
        assert ops and used <= ADDITIVE_OPS | {"execute"}, f"{name}: {sorted(used)}"
        for c in (c for c in ops if c.func.attr == "execute"):
            sql = _literal_string(c.args[0]) if len(c.args) == 1 and not c.keywords else None
            assert _allowed(sql), f"{name}: op.execute is allowed only for a literal CREATE FUNCTION or CREATE " \
                "TRIGGER statement whose name is in DB_OBJECTS"
        for c in (c for c in ops if c.func.attr == "add_column"):
            col = c.args[1]
            kw = {k.arg: k.value for k in col.keywords}
            nullable = isinstance(kw.get("nullable"), ast.Constant) and kw["nullable"].value is True
            assert nullable or "server_default" in kw, f"{name}: add_column needs nullable=True or a server_default"
