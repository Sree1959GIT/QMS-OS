"""baseline schema

Generated with `alembic revision --autogenerate` against an empty PostgreSQL 17 test database, then reviewed by
hand: the circular departments.head_user_id -> users.id key (use_alter) is added after both tables exist.

Revision ID: 7f29c1686517
Revises: 
Create Date: 2026-10-05 22:11:26.160978
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7f29c1686517'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('departments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('head_user_id', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('holidays',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('day')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=200), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=True),
    sa.Column('trained_auditor', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_foreign_key('departments_head_user_id_fkey', 'departments', 'users', ['head_user_id'], ['id'])
    op.create_table('audit_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('entity', sa.String(length=32), nullable=False),
    sa.Column('entity_id', sa.Integer(), nullable=True),
    sa.Column('detail', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('notifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=32), nullable=False),
    sa.Column('to', sa.Text(), nullable=False),
    sa.Column('subject', sa.String(length=300), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('entity', sa.String(length=32), nullable=False),
    sa.Column('entity_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('decided_by_id', sa.Integer(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['decided_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('policy_submissions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('policy_id', sa.String(length=120), nullable=False),
    sa.Column('policy_version', sa.String(length=60), nullable=False),
    sa.Column('effective_date', sa.Date(), nullable=False),
    sa.Column('fingerprint', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('submitted_by_id', sa.Integer(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('submit_note', sa.Text(), nullable=False),
    sa.Column('decided_by_id', sa.Integer(), nullable=True),
    sa.Column('decided_by_name', sa.String(length=120), nullable=False),
    sa.Column('decided_role', sa.String(length=16), nullable=False),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('decision_note', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['decided_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['submitted_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('projects',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=False),
    sa.Column('manager_user_id', sa.Integer(), nullable=False),
    sa.Column('assignment_basis', sa.String(length=24), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['manager_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('audit_programs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('approved_by_id', sa.Integer(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('policy_basis', sa.String(length=16), nullable=False),
    sa.Column('policy_fingerprint', sa.String(length=64), nullable=True),
    sa.Column('policy_submission_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['policy_submission_id'], ['policy_submissions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('year')
    )
    op.create_table('risks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('process', sa.String(length=200), nullable=False),
    sa.Column('failure_mode', sa.Text(), nullable=False),
    sa.Column('effect', sa.Text(), nullable=False),
    sa.Column('cause', sa.Text(), nullable=False),
    sa.Column('current_controls', sa.Text(), nullable=False),
    sa.Column('severity', sa.Integer(), nullable=False),
    sa.Column('occurrence', sa.Integer(), nullable=False),
    sa.Column('detection', sa.Integer(), nullable=False),
    sa.Column('rpn', sa.Integer(), nullable=False),
    sa.Column('proposed_classification', sa.String(length=1), nullable=True),
    sa.Column('effective_classification', sa.String(length=1), nullable=True),
    sa.Column('mitigation_plan', sa.Text(), nullable=False),
    sa.Column('mitigation_due', sa.Date(), nullable=True),
    sa.Column('evidence_ref', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('assessment_version', sa.Integer(), nullable=False),
    sa.Column('policy_fingerprint', sa.String(length=64), nullable=True),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('ma_reviewed_by_id', sa.Integer(), nullable=True),
    sa.Column('signed_off_by_id', sa.Integer(), nullable=True),
    sa.Column('review_due', sa.Date(), nullable=True),
    sa.Column('last_approved_version', sa.Integer(), nullable=True),
    sa.Column('last_approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_approved_by_id', sa.Integer(), nullable=True),
    sa.Column('last_approved_policy_fingerprint', sa.String(length=64), nullable=True),
    sa.Column('last_approved_classification', sa.String(length=1), nullable=True),
    sa.Column('last_approved_ratings', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['last_approved_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['ma_reviewed_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['signed_off_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('audit_cycles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('program_id', sa.Integer(), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=16), nullable=False),
    sa.ForeignKeyConstraint(['program_id'], ['audit_programs.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('risk_assessment_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('risk_id', sa.Integer(), nullable=False),
    sa.Column('assessment_version', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=24), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=False),
    sa.Column('actor_role', sa.String(length=24), nullable=False),
    sa.Column('scope', sa.String(length=64), nullable=False),
    sa.Column('severity', sa.Integer(), nullable=False),
    sa.Column('occurrence', sa.Integer(), nullable=False),
    sa.Column('detection', sa.Integer(), nullable=False),
    sa.Column('rpn', sa.Integer(), nullable=False),
    sa.Column('classification', sa.String(length=1), nullable=True),
    sa.Column('policy_fingerprint', sa.String(length=64), nullable=True),
    sa.Column('evidence_ref', sa.Text(), nullable=False),
    sa.Column('decision', sa.String(length=16), nullable=False),
    sa.Column('note', sa.Text(), nullable=False),
    sa.Column('stale', sa.Boolean(), nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['risk_id'], ['risks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('audits',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cycle_id', sa.Integer(), nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=False),
    sa.Column('auditor_id', sa.Integer(), nullable=True),
    sa.Column('notify_on', sa.Date(), nullable=False),
    sa.Column('evidence_due', sa.Date(), nullable=False),
    sa.Column('audit_date', sa.Date(), nullable=False),
    sa.Column('report_due', sa.Date(), nullable=False),
    sa.Column('action_plan_due', sa.Date(), nullable=False),
    sa.Column('closure_limit', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('reported_on', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['auditor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['cycle_id'], ['audit_cycles.id'], ),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('cycle_id', 'department_id')
    )
    op.create_table('findings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('audit_id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('category', sa.String(length=16), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('statement', sa.Text(), nullable=False),
    sa.Column('objective_evidence', sa.Text(), nullable=False),
    sa.Column('iso_clause', sa.String(length=16), nullable=False),
    sa.Column('qms_ref', sa.String(length=120), nullable=False),
    sa.Column('concurred', sa.Boolean(), nullable=True),
    sa.Column('concurrence_note', sa.Text(), nullable=False),
    sa.Column('repeat_of_id', sa.Integer(), nullable=True),
    sa.Column('reported_on', sa.Date(), nullable=True),
    sa.Column('closed_on', sa.Date(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['audit_id'], ['audits.id'], ),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['repeat_of_id'], ['findings.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('workpapers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('audit_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['audit_id'], ['audits.id'], ),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('corrective_actions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('finding_id', sa.Integer(), nullable=False),
    sa.Column('containment', sa.Text(), nullable=False),
    sa.Column('root_cause', sa.Text(), nullable=False),
    sa.Column('correction', sa.Text(), nullable=False),
    sa.Column('corrective_action', sa.Text(), nullable=False),
    sa.Column('owner_name', sa.String(length=120), nullable=False),
    sa.Column('planned_closure', sa.Date(), nullable=False),
    sa.Column('related_risks', sa.Text(), nullable=False),
    sa.Column('submitted_by_id', sa.Integer(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('accepted_by_id', sa.Integer(), nullable=True),
    sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('closure_evidence_ref', sa.Text(), nullable=False),
    sa.Column('closure_note', sa.Text(), nullable=False),
    sa.Column('verified_by_id', sa.Integer(), nullable=True),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('verification_note', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['accepted_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ),
    sa.ForeignKeyConstraint(['submitted_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['verified_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('finding_id')
    )
    op.create_table('finding_risks',
    sa.Column('finding_id', sa.Integer(), nullable=False),
    sa.Column('risk_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ),
    sa.ForeignKeyConstraint(['risk_id'], ['risks.id'], ),
    sa.PrimaryKeyConstraint('finding_id', 'risk_id')
    )
    op.create_table('kn_sources',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('kind', sa.String(length=32), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('kn_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('doc_number', sa.String(length=64), nullable=False),
    sa.Column('doc_type', sa.String(length=8), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('version', sa.String(length=16), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('origin', sa.Text(), nullable=False),
    sa.Column('captured_by', sa.String(length=120), nullable=False),
    sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('approved_by', sa.String(length=120), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('supersedes_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['source_id'], ['kn_sources.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # No destructive downgrade: records are never deleted (docs/DECISIONS.md D-14). A reviewed,
    # non-destructive downgrade may replace this only with Admin authorisation.
    raise NotImplementedError("downgrade is not supported; restore from a backup instead")
