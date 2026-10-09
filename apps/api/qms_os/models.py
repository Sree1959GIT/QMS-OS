"""System-of-record tables. Portable SQL (SQLite for local dev/tests, PostgreSQL target)."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Column, Date, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy import false as sa_false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .timeutil import UTCDateTime, utcnow


def now() -> datetime:
    return utcnow()


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    head_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", use_alter=True))


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    role: Mapped[str] = mapped_column(String(16))             # rules.findings.Role
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    trained_auditor: Mapped[bool] = mapped_column(Boolean, default=False)
    # account administration, deliberately separate from the QMS role: "account_admin" grants no QMS approval right
    platform_role: Mapped[str] = mapped_column(String(16), default="none", server_default="none")
    department: Mapped[Department | None] = relationship(foreign_keys=[department_id])


class Holiday(Base):
    __tablename__ = "holidays"
    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True)
    name: Mapped[str] = mapped_column(String(120))


class AuditProgram(Base):
    __tablename__ = "audit_programs"
    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, unique=True)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")   # DRAFT | APPROVED
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    # which policy the programme was planned/approved under: "organisation" or "synthetic-demo"
    policy_basis: Mapped[str] = mapped_column(String(16), default="")
    policy_fingerprint: Mapped[str | None] = mapped_column(String(64))
    policy_submission_id: Mapped[int | None] = mapped_column(ForeignKey("policy_submissions.id"))
    cycles: Mapped[list[AuditCycle]] = relationship(back_populates="program", order_by="AuditCycle.seq",
                                                      cascade="all, delete-orphan")


class AuditCycle(Base):
    __tablename__ = "audit_cycles"
    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("audit_programs.id"))
    seq: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    program: Mapped[AuditProgram] = relationship(back_populates="cycles")
    audits: Mapped[list[Audit]] = relationship(back_populates="cycle", order_by="Audit.audit_date",
                                                 cascade="all, delete-orphan")


class Audit(Base):
    __tablename__ = "audits"
    __table_args__ = (UniqueConstraint("cycle_id", "department_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("audit_cycles.id"))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    auditor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    notify_on: Mapped[date] = mapped_column(Date)
    evidence_due: Mapped[date] = mapped_column(Date)
    audit_date: Mapped[date] = mapped_column(Date)
    report_due: Mapped[date] = mapped_column(Date)
    action_plan_due: Mapped[date] = mapped_column(Date)
    closure_limit: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="PLANNED")  # PLANNED | REPORTED
    reported_on: Mapped[date | None] = mapped_column(Date)
    cycle: Mapped[AuditCycle] = relationship(back_populates="audits")
    department: Mapped[Department] = relationship()
    auditor: Mapped[User | None] = relationship()


class Project(Base):
    """A project with an assigned project manager, who owns the project's risks (R-10).
    ``assignment_basis`` records where the manager assignment came from: "synthetic-fixture" in
    demo/test data. An organisational project/PM assignment workflow is not implemented yet
    (docs/DECISIONS.md D-16), so project-risk submission is held in operational mode."""
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    manager_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assignment_basis: Mapped[str] = mapped_column(String(24))
    department: Mapped[Department] = relationship()


class Workpaper(Base):
    """Auditor-only pre-audit material (checklist, questions). Never visible to the auditee
    (VREF-16)."""
    __tablename__ = "workpapers"
    id: Mapped[int] = mapped_column(primary_key=True)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"))
    kind: Mapped[str] = mapped_column(String(16))   # checklist | questions | notes
    content: Mapped[str] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)


finding_risks = Table(
    "finding_risks", Base.metadata,
    Column("finding_id", ForeignKey("findings.id"), primary_key=True),
    Column("risk_id", ForeignKey("risks.id"), primary_key=True),
)


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(primary_key=True)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"))
    code: Mapped[str] = mapped_column(String(64), unique=True)
    category: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")
    statement: Mapped[str] = mapped_column(Text)
    objective_evidence: Mapped[str] = mapped_column(Text, default="")
    iso_clause: Mapped[str] = mapped_column(String(16), default="")
    qms_ref: Mapped[str] = mapped_column(String(120), default="")
    concurred: Mapped[bool | None] = mapped_column(Boolean)
    concurrence_note: Mapped[str] = mapped_column(Text, default="")
    repeat_of_id: Mapped[int | None] = mapped_column(ForeignKey("findings.id"))
    reported_on: Mapped[date | None] = mapped_column(Date)
    closed_on: Mapped[date | None] = mapped_column(Date)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    audit: Mapped[Audit] = relationship()
    action: Mapped[CorrectiveAction | None] = relationship(back_populates="finding", uselist=False)
    risks: Mapped[list[Risk]] = relationship(secondary=finding_risks, back_populates="findings")


class CorrectiveAction(Base):
    """Auditee section of the NCR (VREF-06, auditee section)."""
    __tablename__ = "corrective_actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"), unique=True)
    containment: Mapped[str] = mapped_column(Text, default="")
    root_cause: Mapped[str] = mapped_column(Text)
    correction: Mapped[str] = mapped_column(Text, default="")
    corrective_action: Mapped[str] = mapped_column(Text)
    owner_name: Mapped[str] = mapped_column(String(120))
    planned_closure: Mapped[date] = mapped_column(Date)
    related_risks: Mapped[str] = mapped_column(Text, default="")
    submitted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    accepted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    accepted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    closure_evidence_ref: Mapped[str] = mapped_column(Text, default="")
    closure_note: Mapped[str] = mapped_column(Text, default="")
    verified_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    verification_note: Mapped[str] = mapped_column(Text, default="")
    finding: Mapped[Finding] = relationship(back_populates="action")


class Risk(Base):
    __tablename__ = "risks"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))   # project scope, if any
    process: Mapped[str] = mapped_column(String(200))
    failure_mode: Mapped[str] = mapped_column(Text)
    effect: Mapped[str] = mapped_column(Text, default="")
    cause: Mapped[str] = mapped_column(Text, default="")
    current_controls: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[int] = mapped_column(Integer)
    occurrence: Mapped[int] = mapped_column(Integer)
    detection: Mapped[int] = mapped_column(Integer)
    rpn: Mapped[int] = mapped_column(Integer)
    # proposed = computed from the owner's ratings under an effective scoring policy (None otherwise);
    # effective = issued only at Top Management sign-off (docs/DECISIONS.md R-10)
    proposed_classification: Mapped[str | None] = mapped_column(String(1))
    effective_classification: Mapped[str | None] = mapped_column(String(1))
    mitigation_plan: Mapped[str] = mapped_column(Text, default="")
    mitigation_due: Mapped[date | None] = mapped_column(Date)
    evidence_ref: Mapped[str] = mapped_column(Text, default="")
    # DRAFT -> SUBMITTED -> MA_REVIEWED -> ACTIVE -> CLOSED; any change returns to DRAFT (new version)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    assessment_version: Mapped[int] = mapped_column(Integer, default=1)
    policy_fingerprint: Mapped[str | None] = mapped_column(String(64))   # scoring policy at submission
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ma_reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    signed_off_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    review_due: Mapped[date | None] = mapped_column(Date)
    # snapshot of the most recent signed-off assessment; kept (and shown as "last approved — under
    # reassessment") while a newer version is being reassessed
    last_approved_version: Mapped[int | None] = mapped_column(Integer)
    last_approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    last_approved_policy_fingerprint: Mapped[str | None] = mapped_column(String(64))
    last_approved_classification: Mapped[str | None] = mapped_column(String(1))
    last_approved_ratings: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    department: Mapped[Department] = relationship()
    project: Mapped[Project | None] = relationship()
    findings: Mapped[list[Finding]] = relationship(secondary=finding_risks, back_populates="risks")


class Notification(Base):
    """Outbound message drafts. Nothing leaves the system without human approval
    (VREF-16); the MVP has no mail transport at all."""
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))
    to: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")   # DRAFT | APPROVED | DISCARDED
    entity: Mapped[str] = mapped_column(String(32), default="")
    entity_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class RiskAssessmentRecord(Base):
    """Append-only record of every risk assessment action: actor, role, scope, version, ratings,
    scoring-policy fingerprint, evidence and decision (docs/DECISIONS.md R-10)."""
    __tablename__ = "risk_assessment_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id"))
    assessment_version: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(24))
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str] = mapped_column(String(24))
    scope: Mapped[str] = mapped_column(String(64))
    severity: Mapped[int] = mapped_column(Integer)
    occurrence: Mapped[int] = mapped_column(Integer)
    detection: Mapped[int] = mapped_column(Integer)
    rpn: Mapped[int] = mapped_column(Integer)
    classification: Mapped[str | None] = mapped_column(String(1))
    policy_fingerprint: Mapped[str | None] = mapped_column(String(64))
    evidence_ref: Mapped[str] = mapped_column(Text, default="")
    decision: Mapped[str] = mapped_column(String(16))
    note: Mapped[str] = mapped_column(Text, default="")
    stale: Mapped[bool] = mapped_column(Boolean, default=False)
    at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)


class PolicySubmission(Base):
    """A loaded organisation policy submitted for, and possibly given, final Top Management approval.
    Bound to the exact fingerprint, version and effective date (docs/DECISIONS.md R-9)."""
    __tablename__ = "policy_submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[str] = mapped_column(String(120))
    policy_version: Mapped[str] = mapped_column(String(60))
    effective_date: Mapped[date] = mapped_column(Date)
    fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="SUBMITTED")  # SUBMITTED | APPROVED | REJECTED | STALE
    submitted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    submit_note: Mapped[str] = mapped_column(Text, default="")
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_by_name: Mapped[str] = mapped_column(String(120), default="")
    decided_role: Mapped[str] = mapped_column(String(16), default="")
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    decision_note: Mapped[str] = mapped_column(Text, default="")


class AuditEvent(Base):
    """Append-only provenance log of every state-changing operation."""
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    # who acted (human | agent | telegram | system) and through which channel (web | cli | telegram | test);
    # NULL on events recorded before R-3
    actor_kind: Mapped[str | None] = mapped_column(String(16))
    channel: Mapped[str | None] = mapped_column(String(16))


# ---------- authentication (docs/adr/0003-auth-dev-identity.md, R-3) ----------
# Rows are never deleted (D-14): sessions are revoked, recovery codes and one-time links are marked used.

class UserCredential(Base):
    """Secrets of a human account, kept out of the users table so they never reach a user row in the API."""
    __tablename__ = "user_credentials"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="invited")      # invited | active | disabled
    password_hash: Mapped[str | None] = mapped_column(Text)                  # Argon2id, encoded
    password_changed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    totp_secret_enc: Mapped[str | None] = mapped_column(Text)                # AES-GCM, key file outside Git
    totp_enrolled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    totp_last_step: Mapped[int | None] = mapped_column(Integer)              # single use: last accepted step
    # new secret until its first code is confirmed
    totp_pending_enc: Mapped[str | None] = mapped_column(Text)
    must_reenroll_totp: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)


class AuthIdentity(Base):
    """How a person signs in. A local account has provider and subject NULL; an OIDC identity later records
    (issuer, subject). Accounts are never linked by e-mail address."""
    __tablename__ = "auth_identities"
    __table_args__ = (UniqueConstraint("provider", "subject"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(16))                            # local | oidc
    provider: Mapped[str | None] = mapped_column(String(200))
    subject: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)         # SHA-256 of the cookie token
    csrf_hash: Mapped[str] = mapped_column(String(64))
    method: Mapped[str] = mapped_column(String(24))                          # password_totp | recovery_code
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    idle_expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    absolute_expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    mfa_at: Mapped[datetime | None] = mapped_column(UTCDateTime)             # last TOTP; never set by a recovery code
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    revoked_reason: Mapped[str] = mapped_column(String(32), default="")


class RecoveryCode(Base):
    """120-bit single-use codes, stored as SHA-256 (approved alternative to Argon2id: at least 112 bits)."""
    __tablename__ = "recovery_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    superseded_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class AccountAction(Base):
    """An invitation or a credential reset, with its one-time link. A reset is initiated by one account admin and
    approved by a different one; the person then sets their own password and enrols TOTP through the link."""
    __tablename__ = "account_actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))                            # invite | reset
    target_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # pending_approval | link_issued | completed | superseded | void
    status: Mapped[str] = mapped_column(String(16))
    initiated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    initiated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    identity_proof: Mapped[str] = mapped_column(Text, default="")            # in-person identity check, as recorded
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    link_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    link_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    # verification code (link-code slice): issued to the initiator at request time and needed with the link token;
    # stored only as Argon2id; it expires with the link. A link issued without a code (before this slice) is refused.
    code_hash: Mapped[str | None] = mapped_column(Text)
    code_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # False for the single-admin bootstrap invitation (one admin received both the link and the code) and for rows
    # from before the link-code slice; set explicitly on every new row
    split_knowledge: Mapped[bool] = mapped_column(Boolean, default=True, server_default=sa_false())
    request_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime)   # only while awaiting approval


# ---------- model providers (docs/adr/0005-provider-contract-and-egress.md, R-17 to R-21) ----------
# Rows are never deleted (D-14): an allow-list entry is disabled, not removed; the egress log is append-only.

class ProviderAllowEntry(Base):
    """An admin-approved (provider, model) pair. ``egress_class`` is copied from adapter code when the entry is
    created and must still match it at call time; ``max_data_class`` is the most sensitive data class it may
    receive."""
    __tablename__ = "provider_allow_entries"
    __table_args__ = (UniqueConstraint("provider_id", "model"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(200))
    model_digest: Mapped[str | None] = mapped_column(String(100))        # required for live adapters later (R-21)
    egress_class: Mapped[str] = mapped_column(String(24))                # contract.EgressClass
    max_data_class: Mapped[str] = mapped_column(String(16))              # contract.DataClass
    ceiling_reason: Mapped[str] = mapped_column(Text, default="")        # why a cloud ceiling was raised
    status: Mapped[str] = mapped_column(String(16), default="enabled")   # enabled | disabled
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class ProviderEgressSetting(Base):
    """Global switch for third-party cloud providers: one row (id 1) once an admin has changed it. No row means
    off (R-17)."""
    __tablename__ = "provider_egress_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    third_party_cloud_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class ModelEgressLog(Base):
    """One row per model-call decision (R-18): identifiers and codes only. There is deliberately no text or JSON
    column, so no prompt, response or error message can be stored here (tests/test_providers.py). Written in its
    own committed transaction; an allowed call writes ``dispatched`` before any data leaves, then ``completed`` or
    ``failed``, linked by ``request_id``."""
    __tablename__ = "model_egress_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    request_id: Mapped[str] = mapped_column(String(32), index=True)
    provider_id: Mapped[str | None] = mapped_column(String(64))          # NULL if the caller's value was malformed
    model: Mapped[str | None] = mapped_column(String(200))               # NULL if the caller's value was malformed
    egress_class: Mapped[str | None] = mapped_column(String(24))         # NULL for an unknown provider
    data_class: Mapped[str | None] = mapped_column(String(16))           # NULL if missing or unknown
    outcome: Mapped[str] = mapped_column(String(16))                     # refused | dispatched | completed | failed
    reason: Mapped[str | None] = mapped_column(String(32))               # gateway.REASONS
    integration_mode: Mapped[str | None] = mapped_column(String(16))     # simulated | test | live
    allow_entry_id: Mapped[int | None] = mapped_column(ForeignKey("provider_allow_entries.id"))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    actor_kind: Mapped[str | None] = mapped_column(String(16))
    channel: Mapped[str | None] = mapped_column(String(16))
