#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 PopSolutions Cooperative
#
# run_lint.sh — smoke check for src/intercard_link.sv via Verilator.
#
# Verifies that:
#   1. The intercard_link stub elaborates without errors.
#   2. The MAST #14 width contract (INTERCARD_BUS_WIDTH = 128) holds —
#      enforced by verif/intercard_link/test_widths.sv generate guard.
#
# Exit code 0 on pass, non-zero on failure.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SRC="${REPO_ROOT}/src/intercard_link.sv"
TB="${REPO_ROOT}/verif/intercard_link/test_widths.sv"

if ! command -v verilator >/dev/null 2>&1; then
    echo "[run_lint] verilator not found in PATH; SKIPPING the width-contract gate." >&2
    echo "[run_lint] CI must install Verilator before invoking this script." >&2
    # Exit 77 = POSIX skip code (recognised by automake/autotest and many CIs).
    # Hard-fail rather than silent-pass: the gate is silent-skipped, not green.
    exit 77
fi

echo "[run_lint] verilator $(verilator --version | head -1)"
echo "[run_lint] linting ${SRC} with top ${TB}"

verilator --lint-only \
    --top-module test_widths \
    -Wall \
    -Wno-DECLFILENAME \
    -Wno-UNUSED \
    "${SRC}" "${TB}"

echo "[run_lint] PASS — intercard_link elaborates with INTERCARD_BUS_WIDTH = 128"
