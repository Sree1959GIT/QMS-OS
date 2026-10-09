"""provider allow-list and egress log

Generated with `alembic revision --autogenerate` against the PostgreSQL test database at c5ee69870dbb and
reviewed by hand. Additive only: three new tables for the model-provider contract
(docs/adr/0005-provider-contract-and-egress.md): provider_allow_entries, provider_egress_settings (no row means
third-party cloud is off) and the append-only model_egress_log, which has no text or JSON column.

Revision ID: 44bca21ba248
Revises: c5ee69870dbb
Create Date: 2026-10-09 18:40:55.616408
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '44bca21ba248'
down_revision: Union[str, Sequence[str], None] = 'c5ee69870dbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('provider_allow_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('provider_id', sa.String(length=64), nullable=False),
    sa.Column('model', sa.String(length=200), nullable=False),
    sa.Column('model_digest', sa.String(length=100), nullable=True),
    sa.Column('egress_class', sa.String(length=24), nullable=False),
    sa.Column('max_data_class', sa.String(length=16), nullable=False),
    sa.Column('ceiling_reason', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_by_id', sa.Integer(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('provider_id', 'model')
    )
    op.create_table('provider_egress_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('third_party_cloud_enabled', sa.Boolean(), nullable=False),
    sa.Column('updated_by_id', sa.Integer(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('model_egress_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('request_id', sa.String(length=32), nullable=False),
    sa.Column('provider_id', sa.String(length=64), nullable=True),
    sa.Column('model', sa.String(length=200), nullable=True),
    sa.Column('egress_class', sa.String(length=24), nullable=True),
    sa.Column('data_class', sa.String(length=16), nullable=True),
    sa.Column('outcome', sa.String(length=16), nullable=False),
    sa.Column('reason', sa.String(length=32), nullable=True),
    sa.Column('integration_mode', sa.String(length=16), nullable=True),
    sa.Column('allow_entry_id', sa.Integer(), nullable=True),
    sa.Column('actor_id', sa.Integer(), nullable=True),
    sa.Column('actor_kind', sa.String(length=16), nullable=True),
    sa.Column('channel', sa.String(length=16), nullable=True),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['allow_entry_id'], ['provider_allow_entries.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_model_egress_log_request_id', 'model_egress_log', ['request_id'], unique=False)


def downgrade() -> None:
    # No destructive downgrade: records are never deleted (docs/DECISIONS.md D-14). A reviewed,
    # non-destructive downgrade may replace this only with Admin authorisation.
    raise NotImplementedError("downgrade is not supported; restore from a backup instead")
