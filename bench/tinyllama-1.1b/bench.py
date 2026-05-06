#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-SA-4.0
"""TinyLlama-1.1B int4 reference workload — baseline harness.

Runs ``N_TOKENS`` of decode against a fixed prompt and emits a JSON document
with the timing measurement on stdout. See ``README.md`` for the full schema
and the migration path to InnerJib7EA / Spanker hardware.

Closes part of popsolutions/InnerJib7EA#3.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1"
DEFAULT_PROMPT = "Hello, "
DEFAULT_N_TOKENS = 64
DEFAULT_SEED = 42

# --- Host metadata ----------------------------------------------------------


def _detect_cpu_model() -> str:
    """Best-effort CPU model name. Falls back to platform.processor()."""
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        try:
            for line in cpuinfo.read_text().splitlines():
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
        except OSError:
            pass
    return platform.processor() or "unknown"


def _detect_ram_gb() -> float:
    """Best-effort total RAM in GB (binary GB)."""
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        try:
            for line in meminfo.read_text().splitlines():
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return round(kb / 1024 / 1024, 2)
        except (OSError, ValueError, IndexError):
            pass
    return 0.0


def _host_metadata() -> dict[str, Any]:
    return {
        "cpu": _detect_cpu_model(),
        "cores": os.cpu_count() or 0,
        "ram_gb": _detect_ram_gb(),
    }


# --- Backends ---------------------------------------------------------------


def _llama_cpp_python_version() -> str:
    try:
        import llama_cpp  # type: ignore[import-not-found]
        return getattr(llama_cpp, "__version__", "unknown")
    except ImportError:
        return "not-installed"


def run_backend_llama_cpp_python(
    model_path: Path, prompt: str, n_tokens: int, seed: int
) -> tuple[float, int]:
    """Run decode via llama-cpp-python. Returns (wall_seconds, tokens_generated)."""
    try:
        from llama_cpp import Llama  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError(
            "llama-cpp-python is not installed. "
            "Install it with: pip install llama-cpp-python==0.2.90"
        ) from e

    llm = Llama(
        model_path=str(model_path),
        n_ctx=512,
        n_threads=os.cpu_count() or 4,
        seed=seed,
        verbose=False,
    )

    # Prompt eval (warm-up); we time decode only, per the README schema.
    _ = llm(prompt, max_tokens=1, echo=False)

    start = time.perf_counter()
    out = llm(prompt, max_tokens=n_tokens, echo=False)
    elapsed = time.perf_counter() - start

    # Llama returns OpenAI-shaped completion; tokens-emitted lives in usage.
    tokens_generated = int(
        out.get("usage", {}).get("completion_tokens", n_tokens)
    )
    return elapsed, tokens_generated


def run_backend_llama_cli(
    model_path: Path,
    prompt: str,
    n_tokens: int,
    seed: int,
    binary_path: str,
) -> tuple[float, int]:
    """Run decode via the llama-cli binary. Returns (wall_seconds, tokens_generated)."""
    if not shutil.which(binary_path) and not Path(binary_path).is_file():
        raise RuntimeError(
            f"llama-cli binary not found at {binary_path}. "
            "Pass --llama-cli-path or install llama.cpp."
        )

    cmd = [
        binary_path,
        "--model", str(model_path),
        "--prompt", prompt,
        "--n-predict", str(n_tokens),
        "--seed", str(seed),
        "--threads", str(os.cpu_count() or 4),
        "--no-display-prompt",
        "--log-disable",
    ]

    start = time.perf_counter()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
    )
    elapsed = time.perf_counter() - start

    # llama-cli does not give us a clean token count; use the requested budget.
    # This is acceptable for decode-rate measurement: we asked for n_tokens and
    # the binary stops at that count.
    _ = result.stdout
    tokens_generated = n_tokens
    return elapsed, tokens_generated


# --- Dry-run backend (for schema test) --------------------------------------


def run_backend_dry_run(
    model_path: Path, prompt: str, n_tokens: int, seed: int
) -> tuple[float, int]:
    """Synthetic backend — no model needed. Used by test_bench.py for schema test."""
    # Pretend we generated n_tokens at a deterministic synthetic rate.
    synthetic_rate = 10.0  # tokens/sec
    return n_tokens / synthetic_rate, n_tokens


# --- Schema construction ----------------------------------------------------


def build_record(
    *,
    model_path: Path,
    backend: str,
    prompt: str,
    tokens_generated: int,
    wall_clock_seconds: float,
    llama_cpp_version: str,
) -> dict[str, Any]:
    tps = tokens_generated / wall_clock_seconds if wall_clock_seconds > 0 else 0.0
    return {
        "schema_version": SCHEMA_VERSION,
        "model": model_path.name,
        "backend": backend,
        "prompt": prompt,
        "tokens_generated": tokens_generated,
        "wall_clock_seconds": round(wall_clock_seconds, 4),
        "tokens_per_second": round(tps, 4),
        "host": _host_metadata(),
        "llama_cpp_version": llama_cpp_version,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# --- Threshold check --------------------------------------------------------


def check_threshold(record: dict[str, Any], baseline_path: Path) -> tuple[bool, str]:
    """Return (passed, message)."""
    try:
        baseline = json.loads(baseline_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return False, f"could not load baseline {baseline_path}: {e}"

    min_tps = float(baseline.get("min_tokens_per_sec", 0.0))
    measured_tps = float(record["tokens_per_second"])

    if measured_tps < min_tps:
        return False, (
            f"FAIL: measured {measured_tps:.2f} tok/s < threshold {min_tps:.2f} tok/s"
        )
    return True, f"PASS: measured {measured_tps:.2f} tok/s >= threshold {min_tps:.2f} tok/s"


# --- CLI --------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--model",
        type=Path,
        default=Path(__file__).parent / "tinyllama-1.1b-chat-v1.0.Q4_0.gguf",
        help="Path to the GGUF model file.",
    )
    p.add_argument(
        "--backend",
        choices=["llama-cpp-python", "llama-cli", "dry-run"],
        default="llama-cpp-python",
        help="Which backend to use for decode.",
    )
    p.add_argument(
        "--llama-cli-path",
        default="llama-cli",
        help="Path to the llama-cli binary (only used when --backend=llama-cli).",
    )
    p.add_argument("--prompt", default=DEFAULT_PROMPT)
    p.add_argument("--n-tokens", type=int, default=DEFAULT_N_TOKENS)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument(
        "--check",
        type=Path,
        default=None,
        help="Path to expected_baseline.json. Exits non-zero if measured < threshold.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip the actual model run; emit a synthetic record. For schema tests.",
    )
    args = p.parse_args(argv)

    backend = "dry-run" if args.dry_run else args.backend

    if backend != "dry-run" and not args.model.is_file():
        print(
            f"ERROR: model file not found at {args.model}. "
            f"Run ./fetch_model.sh first.",
            file=sys.stderr,
        )
        return 2

    if backend == "dry-run":
        elapsed, tokens = run_backend_dry_run(
            args.model, args.prompt, args.n_tokens, args.seed
        )
        version = "dry-run"
    elif backend == "llama-cpp-python":
        elapsed, tokens = run_backend_llama_cpp_python(
            args.model, args.prompt, args.n_tokens, args.seed
        )
        version = _llama_cpp_python_version()
    elif backend == "llama-cli":
        elapsed, tokens = run_backend_llama_cli(
            args.model, args.prompt, args.n_tokens, args.seed, args.llama_cli_path
        )
        version = "llama-cli"
    else:
        print(f"ERROR: unknown backend {backend}", file=sys.stderr)
        return 2

    record = build_record(
        model_path=args.model,
        backend=backend,
        prompt=args.prompt,
        tokens_generated=tokens,
        wall_clock_seconds=elapsed,
        llama_cpp_version=version,
    )

    print(json.dumps(record, indent=2, sort_keys=True))

    if args.check is not None:
        passed, message = check_threshold(record, args.check)
        print(message, file=sys.stderr)
        return 0 if passed else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
