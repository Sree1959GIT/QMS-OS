"""auth accounts and sessions (R-3)

Generated with `alembic revision --autogenerate` against the PostgreSQL test database at 7f29c1686517 and
reviewed by hand. Additive only: five new tables, plus three columns on existing tables that the approved R-3 design
needs (users.platform_role with a server default; audit_events.actor_kind and .channel, NULL on earlier events).

Revision ID: 0b13751a07cc
Revises: 7f29c1686517
Create Date: 2026-10-06 13:46:36.408358
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0b13751a07cc'
down_revision: Union[str, Sequence[str], None] = '7f29c1686517'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('account_actions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('target_user_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('initiated_by_id', sa.Integer(), nullable=True),
    sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('identity_proof', sa.Text(), nullable=False),
    sa.Column('approved_by_id', sa.Integer(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('link_hash', sa.String(length=64), nullable=True),
    sa.Column('link_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['initiated_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('link_hash')
    )
    op.create_table('auth_identities',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('provider', sa.String(length=200), nullable=True),
    sa.Column('subject', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('provider', 'subject')
    )
    op.create_table('auth_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('csrf_hash', sa.String(length=64), nullable=False),
    sa.Column('method', sa.String(length=24), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('idle_expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('absolute_expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('mfa_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_reason', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_table('recovery_codes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code_hash')
    )
    op.create_table('user_credentials',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=True),
    sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('totp_secret_enc', sa.Text(), nullable=True),
    sa.Column('totp_enrolled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('totp_last_step', sa.Integer(), nullable=True),
    sa.Column('totp_pending_enc', sa.Text(), nullable=True),
    sa.Column('must_reenroll_totp', sa.Boolean(), nullable=False),
    sa.Column('failed_attempts', sa.Integer(), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.add_column('audit_events', sa.Column('actor_kind', sa.String(length=16), nullable=True))
    op.add_column('audit_events', sa.Column('channel', sa.String(length=16), nullable=True))
    op.add_column('users', sa.Column('platform_role', sa.String(length=16), server_default='none', nullable=False))


def downgrade() -> None:
    # No destructive downgrade: records are never deleted (docs/DECISIONS.md D-14). A reviewed,
    # non-destructive downgrade may replace this only with Admin authorisation.
    raise NotImplementedError("downgrade is not supported; restore from a backup instead")
