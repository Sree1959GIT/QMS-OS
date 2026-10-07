"""account action verification code

Generated with `alembic revision --autogenerate` against the PostgreSQL test database at 0b13751a07cc and
reviewed by hand. Additive only: four nullable or server-defaulted columns on account_actions. Rows from before this
migration get split_knowledge = false (their link went to one admin, without a code) and no code_hash, so their
links are refused and must be issued again.

Revision ID: c5ee69870dbb
Revises: 0b13751a07cc
Create Date: 2026-10-07 15:46:54.325025
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5ee69870dbb'
down_revision: Union[str, Sequence[str], None] = '0b13751a07cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('account_actions', sa.Column('code_hash', sa.Text(), nullable=True))
    op.add_column('account_actions', sa.Column('code_attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('account_actions', sa.Column('split_knowledge', sa.Boolean(), server_default=sa.text('false'),
                                               nullable=False))
    op.add_column('account_actions', sa.Column('request_expires_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # No destructive downgrade: records are never deleted (docs/DECISIONS.md D-14). A reviewed,
    # non-destructive downgrade may replace this only with Admin authorisation.
    raise NotImplementedError("downgrade is not supported; restore from a backup instead")
