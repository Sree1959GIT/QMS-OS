"""QMS OS knowledge infrastructure — an independent module.

Boundaries (see docs/adr/0004-independent-knowledge-module.md):
- Owns its own tables (``kn_*``) and SQLAlchemy metadata; it imports nothing
  from the audit/risk domain and the domain imports nothing from it. The API
  layer is the only place both meet.
- Every item carries provenance and an approval status. Content enters as
  ``candidate``; only ``approved`` items are returned for citation by default;
  superseded items become ``obsolete`` and are retained, never deleted
  (Documented Information control: prevent unintended use of obsolete info).
- There is deliberately NO importer, sync job or runtime link to any external
  repository (including the development-reference audit vault). Migration of
  approved material is a later, separately reviewed phase
  (docs/05-knowledge-roadmap.md).
"""
from .service import KnowledgeService, KnowledgeError, ApprovalStatus  # noqa: F401
