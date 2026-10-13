"""Local-model benchmark harness and its test-mode adapter (ROADMAP MVP-0 slice 4b; docs/BENCHMARK-PLAN.md,
section 7). Run by the Admin with ``python -m qms_bench`` from ``apps/api``.

A package of its own, outside ``qms_os``: the application package holds no HTTP client
(tests/test_knowledge_module.py) and never imports this one (tests/test_benchmark_harness.py)."""
