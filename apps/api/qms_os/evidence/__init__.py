"""Original-evidence store (MVP-1 slice 5; R-34, R-50 to R-54): an adapter interface and an interim local
content-addressed store for synthetic fixtures only. PostgreSQL holds each object's metadata (``evidence_objects``);
the store holds the bytes, named by their SHA-256."""
