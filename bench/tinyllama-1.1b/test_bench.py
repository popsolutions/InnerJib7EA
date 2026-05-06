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
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


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
