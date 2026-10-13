"""Command line for the benchmark harness (docs/BENCHMARK-PLAN.md, section 7 "Harness").

    python -m qms_bench --list-models [--endpoint URL]
    python -m qms_bench --model NAME --model-digest sha256:HEX --power-mode TEXT --plugged-in yes|no
        --gpu-temp-c N --gpu-in-use TEXT [--endpoint URL] [--repetitions N] [--warmup N] [--num-predict N]
        [--contexts 4096,8192] [--timeout S] [--out DIR]

Exit codes: 0 done, 2 usage error, 3 refused or failed before or during the run.
"""
from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from qms_os.providers.gateway import ProviderRefused

from .harness import (
    DEFAULT_ENDPOINT,
    DEFAULT_NUM_PREDICT,
    DEFAULT_OUT_ROOT,
    DEFAULT_REPETITIONS,
    DEFAULT_WARMUP,
    Harness,
    HarnessError,
    RunMeta,
    format_table,
)
from .ollama_adapter import EndpointRefused


def _contexts(value: str) -> list[int]:
    try:
        return [int(v) for v in value.split(",") if v.strip()]
    except ValueError:
        raise argparse.ArgumentTypeError("a comma-separated list of integers") from None


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m qms_bench", description="B4 and B5 benchmark cells against a "
                                "loopback Ollama-compatible endpoint, through the provider gateway (test mode).")
    p.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help=f"loopback only (default {DEFAULT_ENDPOINT})")
    p.add_argument("--list-models", action="store_true", help="print the endpoint's models and digests, then stop")
    p.add_argument("--model")
    p.add_argument("--model-digest", help="sha256 digest of the model, 64 hex characters (R-21)")
    p.add_argument("--power-mode")
    p.add_argument("--plugged-in", choices=("yes", "no"))
    p.add_argument("--gpu-temp-c")
    p.add_argument("--gpu-in-use")
    p.add_argument("--repetitions", type=int, default=DEFAULT_REPETITIONS)
    p.add_argument("--warmup", type=int, default=DEFAULT_WARMUP, help="runs per cell before the counted ones")
    p.add_argument("--num-predict", type=int, default=DEFAULT_NUM_PREDICT, help="output cap per request")
    p.add_argument("--contexts", type=_contexts, default=[4096, 8192], help="num_ctx values (default 4096,8192)")
    p.add_argument("--timeout", type=float, default=600.0, help="seconds per HTTP request")
    p.add_argument("--out", type=Path, help=f"new output directory (default {DEFAULT_OUT_ROOT}/<UTC time>)")
    return p


def main(argv: list[str] | None = None) -> int:
    p = parser()
    a = p.parse_args(argv)
    run_flags = ("model", "model_digest", "power_mode", "plugged_in", "gpu_temp_c", "gpu_in_use")
    if not a.list_models:
        missing = [f"--{f.replace('_', '-')}" for f in run_flags if getattr(a, f) is None]
        if missing:
            p.error("missing " + ", ".join(missing))
    out = a.out or DEFAULT_OUT_ROOT / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    try:
        h = Harness(endpoint=a.endpoint, model=a.model or "", model_digest=a.model_digest or "0" * 64,
                    meta=RunMeta(a.power_mode or "", a.plugged_in or "", a.gpu_temp_c or "", a.gpu_in_use or ""),
                    out_dir=out, repetitions=a.repetitions, warmup=a.warmup, num_predict=a.num_predict,
                    contexts=a.contexts, timeout=a.timeout)
        if a.list_models:
            for m in h.list_models():
                print(f"{m.get('name')}\t{m.get('digest')}")
            return 0
        _, rows = h.run()
    except (EndpointRefused, HarnessError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 3
    except ProviderRefused as e:
        print(f"refused by the provider gateway: {e} ({e.reason})", file=sys.stderr)
        return 3
    except OSError as e:
        print(f"failed: {type(e).__name__}", file=sys.stderr)
        return 3
    print(format_table(rows))
    print(f"\nraw records (untracked): {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
