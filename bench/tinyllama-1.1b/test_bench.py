# SPDX-License-Identifier: CC-BY-SA-4.0
"""Schema-only unit tests for bench.py.

These tests do NOT download or run TinyLlama (CI's bench.yml does that on
manual dispatch). They invoke ``bench.py --dry-run`` and assert the JSON
output shape, so downstream tooling (regression tracker, future
``Xpop_matmul`` perf comparison plots) cannot break silently when the
schema changes.

Per ``feedback_testing.md``: every code change ships with a test. For a
benchmark harness, the realistic test is its output schema.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BENCH_PY = Path(__file__).parent / "bench.py"
EXPECTED_BASELINE = Path(__file__).parent / "expected_baseline.json"


def _run_bench(*extra_args: str) -> dict:
    """Invoke bench.py --dry-run and return the parsed JSON record."""
    cmd = [sys.executable, str(BENCH_PY), "--dry-run", *extra_args]
    # 30 s is generous for the dry-run path (no model load). Without a timeout
    # a hang here would block the whole CI job up to its 30-min ceiling.
    result = subprocess.run(
        cmd, capture_output=True, text=True, check=True, timeout=30
    )
    return json.loads(result.stdout)


def _run_bench_with_check(baseline_path: Path, *extra_args: str) -> subprocess.CompletedProcess:
    """Invoke bench.py --dry-run --check <baseline> and return the raw process result.

    Does NOT pass check=True — caller asserts on returncode.
    """
    cmd = [
        sys.executable,
        str(BENCH_PY),
        "--dry-run",
        "--check",
        str(baseline_path),
        *extra_args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


# --- Schema field presence --------------------------------------------------


REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "model",
    "backend",
    "prompt",
    "tokens_generated",
    "wall_clock_seconds",
    "tokens_per_second",
    "host",
    "llama_cpp_version",
    "timestamp_utc",
}

REQUIRED_HOST_FIELDS = {"cpu", "cores", "ram_gb"}


def test_dry_run_produces_valid_json():
    record = _run_bench()
    assert isinstance(record, dict)


def test_all_required_top_level_fields_present():
    record = _run_bench()
    missing = REQUIRED_TOP_LEVEL_FIELDS - record.keys()
    assert not missing, f"missing top-level fields: {missing}"


def test_all_required_host_fields_present():
    record = _run_bench()
    missing = REQUIRED_HOST_FIELDS - record["host"].keys()
    assert not missing, f"missing host fields: {missing}"


# --- Schema field types -----------------------------------------------------


def test_field_types():
    record = _run_bench()
    assert isinstance(record["schema_version"], str)
    assert isinstance(record["model"], str)
    assert isinstance(record["backend"], str)
    assert isinstance(record["prompt"], str)
    assert isinstance(record["tokens_generated"], int)
    assert isinstance(record["wall_clock_seconds"], (int, float))
    assert isinstance(record["tokens_per_second"], (int, float))
    assert isinstance(record["host"], dict)
    assert isinstance(record["host"]["cpu"], str)
    assert isinstance(record["host"]["cores"], int)
    assert isinstance(record["host"]["ram_gb"], (int, float))
    assert isinstance(record["llama_cpp_version"], str)
    assert isinstance(record["timestamp_utc"], str)


# --- Schema field semantics -------------------------------------------------


def test_schema_version_pinned():
    """If we bump the version, downstream consumers must opt in explicitly."""
    record = _run_bench()
    assert record["schema_version"] == "1"


def test_dry_run_backend_marker():
    record = _run_bench()
    assert record["backend"] == "dry-run"


def test_tokens_per_second_matches_division():
    record = _run_bench()
    expected_tps = record["tokens_generated"] / record["wall_clock_seconds"]
    assert record["tokens_per_second"] == pytest.approx(expected_tps, rel=1e-3)


def test_tokens_generated_positive():
    record = _run_bench()
    assert record["tokens_generated"] > 0


def test_wall_clock_seconds_positive():
    record = _run_bench()
    assert record["wall_clock_seconds"] > 0


def test_timestamp_is_iso8601_utc_z():
    """Schema doc promises ISO-8601 UTC with trailing Z. Lock it."""
    record = _run_bench()
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
    assert re.match(pattern, record["timestamp_utc"]), (
        f"timestamp_utc {record['timestamp_utc']!r} does not match {pattern}"
    )


# --- CLI behaviour ----------------------------------------------------------


def test_custom_n_tokens_is_honoured():
    record = _run_bench("--n-tokens", "32")
    assert record["tokens_generated"] == 32


def test_custom_prompt_is_honoured():
    record = _run_bench("--prompt", "Greetings, ")
    assert record["prompt"] == "Greetings, "


# --- Baseline JSON schema ---------------------------------------------------


def test_expected_baseline_loadable():
    """The baseline file must be valid JSON the harness can parse."""
    data = json.loads(EXPECTED_BASELINE.read_text())
    assert "min_tokens_per_sec" in data
    assert isinstance(data["min_tokens_per_sec"], (int, float))
    assert data["min_tokens_per_sec"] > 0


def test_expected_baseline_schema_version_matches():
    """Baseline must agree with bench.py SCHEMA_VERSION; otherwise --check is meaningless."""
    data = json.loads(EXPECTED_BASELINE.read_text())
    record = _run_bench()
    assert data["schema_version"] == record["schema_version"]


# --- check_threshold / --check exit-code path ------------------------------
#
# The dry-run backend in bench.py emits exactly 10.0 tokens/sec
# (synthetic_rate = 10.0, n_tokens generated in n_tokens/10 seconds).
# Tests below pin baselines on either side of that to verify the exit-code
# contract.

DRY_RUN_TOKENS_PER_SEC = 10.0


def _write_baseline(path: Path, **fields) -> Path:
    """Write a minimal baseline JSON with the supplied threshold fields."""
    payload = {"schema_version": "1", **fields}
    path.write_text(json.dumps(payload))
    return path


def test_check_passes_when_min_tps_below_synthetic(tmp_path):
    """Threshold below synthetic rate → exit 0."""
    baseline = _write_baseline(
        tmp_path / "baseline.json",
        min_tokens_per_sec=DRY_RUN_TOKENS_PER_SEC - 1.0,
    )
    result = _run_bench_with_check(baseline)
    assert result.returncode == 0, (
        f"expected exit 0, got {result.returncode}; stderr={result.stderr}"
    )


def test_check_fails_when_min_tps_above_synthetic(tmp_path):
    """Threshold above synthetic rate → non-zero exit + identifying message."""
    baseline = _write_baseline(
        tmp_path / "baseline.json",
        min_tokens_per_sec=DRY_RUN_TOKENS_PER_SEC + 5.0,
    )
    result = _run_bench_with_check(baseline)
    assert result.returncode != 0, (
        f"expected non-zero exit, got 0; stdout={result.stdout}"
    )
    assert "min_tokens_per_sec" in result.stderr
    assert "FAIL" in result.stderr


def test_check_passes_when_max_wall_clock_above_actual(tmp_path):
    """wall_clock ceiling > measured → exit 0."""
    # Default n-tokens=64 → 64/10 = 6.4 s synthetic wall clock.
    baseline = _write_baseline(
        tmp_path / "baseline.json",
        max_wall_clock_seconds=60.0,
    )
    result = _run_bench_with_check(baseline)
    assert result.returncode == 0, (
        f"expected exit 0, got {result.returncode}; stderr={result.stderr}"
    )


def test_check_fails_when_max_wall_clock_below_actual(tmp_path):
    """wall_clock ceiling < measured → non-zero exit + identifying message."""
    baseline = _write_baseline(
        tmp_path / "baseline.json",
        max_wall_clock_seconds=0.1,  # well below 6.4 s synthetic
    )
    result = _run_bench_with_check(baseline)
    assert result.returncode != 0
    assert "max_wall_clock_seconds" in result.stderr
    assert "FAIL" in result.stderr


def test_check_passes_when_tokens_generated_matches_expected(tmp_path):
    """tokens_generated == expected → exit 0."""
    baseline = _write_baseline(
        tmp_path / "baseline.json",
        tokens_generated_expected=64,  # matches default --n-tokens
    )
    result = _run_bench_with_check(baseline)
    assert result.returncode == 0, (
        f"expected exit 0, got {result.returncode}; stderr={result.stderr}"
    )


def test_check_fails_when_tokens_generated_differs_from_expected(tmp_path):
    """tokens_generated != expected → non-zero exit + identifying message."""
    baseline = _write_baseline(
        tmp_path / "baseline.json",
        tokens_generated_expected=999,  # default n-tokens is 64
    )
    result = _run_bench_with_check(baseline)
    assert result.returncode != 0
    assert "tokens_generated_expected" in result.stderr
    assert "FAIL" in result.stderr


def test_check_aggregates_multiple_failures(tmp_path):
    """Multiple violations → all reported in one shot, single non-zero exit."""
    baseline = _write_baseline(
        tmp_path / "baseline.json",
        min_tokens_per_sec=DRY_RUN_TOKENS_PER_SEC + 100.0,
        max_wall_clock_seconds=0.001,
        tokens_generated_expected=1,
    )
    result = _run_bench_with_check(baseline)
    assert result.returncode != 0
    # All three field names should appear in the failure message.
    assert "min_tokens_per_sec" in result.stderr
    assert "max_wall_clock_seconds" in result.stderr
    assert "tokens_generated_expected" in result.stderr


def test_check_with_empty_baseline_passes(tmp_path):
    """No thresholds declared → trivially passes (partial-baseline workflow)."""
    baseline = _write_baseline(tmp_path / "baseline.json")  # only schema_version
    result = _run_bench_with_check(baseline)
    assert result.returncode == 0


# TODO(agent3-followup): Add negative tests for the schema validator
# (malformed records: missing required field, tokens_per_second = -1, etc.)
# tracked separately from this PR per Agent R review scope.
