"""workflow grants and guideline classification

Written by hand against the models at 03c084021bfa (grant-governed workflow reads; R-74, R-75;
docs/adr/0008-grant-governed-workflow-reads.md). Additive only: table workflow_grants (R-74: a table of its own, like
evidence_grants, so role_grants and its CHECK constraint stay unchanged) with CHECK constraints on role and ceiling,
and a classification column on workflow_guidelines with the server default 'internal' (every existing guideline is
internal, as R-64 assumed) and a CHECK constraint, which Alembic adds after the column. No op.execute.

Revision ID: f06d2c9357ad
Revises: 03c084021bfa
Create Date: 2026-10-21 18:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f06d2c9357ad'
down_revision: Union[str, Sequence[str], None] = '03c084021bfa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('workflow_grants',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('max_classification', sa.String(length=16), nullable=False),
    sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("max_classification IN ('public', 'internal', 'confidential')",
                       name='ck_workflow_grants_max_classification'),
    sa.CheckConstraint("role IN ('MA', 'AUDITOR', 'AUDITEE', 'MD', 'VIEWER')", name='ck_workflow_grants_role'),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('workflow_guidelines', sa.Column('classification', sa.String(length=16),
                                                   sa.CheckConstraint("classification IN ('public', 'internal', "
                                                                      "'confidential')",
                                                                      name='ck_workflow_guidelines_classification'),
                                                   server_default='internal', nullable=False))


def downgrade() -> None:
    # No destructive downgrade: records are never deleted (docs/DECISIONS.md D-14). A reviewed,
    # non-destructive downgrade may replace this only with Admin authorisation.
    raise NotImplementedError("downgrade is not supported; restore from a backup instead")
