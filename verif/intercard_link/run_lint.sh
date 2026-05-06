#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 PopSolutions Cooperative
#
# run_lint.sh — smoke check for the role-split intercard_link modules
# via Verilator.
#
# Verifies that:
#   1. Both intercard_link_upstream and intercard_link_downstream stubs
#      elaborate without errors.
#   2. The MAST #14 width contract (INTERCARD_BUS_WIDTH = 128) holds for
#      BOTH modules — enforced by verif/intercard_link/test_widths.sv
#      generate guard.
#   3. The CLK direction split per ADR-003 holds: the upstream module
#      drives clk_p/clk_n out, the downstream module receives them as
#      input. A direction mismatch (e.g., trying to drive a port that
#      is declared `input`) manifests as a Verilator elaboration error
#      when test_widths.sv wires its `wire`/`logic` stimulus to the
#      role ports.
#
# Exit code 0 on pass, non-zero on failure.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SRC_UP="${REPO_ROOT}/src/intercard_link_upstream.sv"
SRC_DN="${REPO_ROOT}/src/intercard_link_downstream.sv"
TB_WIDTHS="${REPO_ROOT}/verif/intercard_link/test_widths.sv"
TB_PAIR="${REPO_ROOT}/verif/intercard_link/test_two_card_pair.sv"

if ! command -v verilator >/dev/null 2>&1; then
    echo "[run_lint] verilator not found in PATH; SKIPPING the width-contract gate." >&2
    echo "[run_lint] CI must install Verilator before invoking this script." >&2
    # Exit 77 = POSIX skip code (recognised by automake/autotest and many CIs).
    # Hard-fail rather than silent-pass: the gate is silent-skipped, not green.
    exit 77
fi

echo "[run_lint] verilator $(verilator --version | head -1)"

# Pass 1: width-contract guard (test_widths) instantiates both role
# variants in parallel and asserts INTERCARD_BUS_WIDTH = 128.
echo "[run_lint] (1/2) widths: ${TB_WIDTHS}"
verilator --lint-only \
    --top-module test_widths \
    -Wall \
    -Wno-DECLFILENAME \
    -Wno-UNUSED \
    "${SRC_UP}" "${SRC_DN}" "${TB_WIDTHS}"

# Pass 2: two-card pair (test_two_card_pair) wires upstream's clk_p/clk_n
# OUTPUT into downstream's clk_p/clk_n INPUT on a single shared net.
# Verilator's multi-driver / direction checks make this elaboration the
# structural assertion that the CLK direction split is correct.
echo "[run_lint] (2/2) two-card pair: ${TB_PAIR}"
verilator --lint-only \
    --top-module test_two_card_pair \
    -Wall \
    -Wno-DECLFILENAME \
    -Wno-UNUSED \
    "${SRC_UP}" "${SRC_DN}" "${TB_PAIR}"

echo "[run_lint] PASS — intercard_link_upstream + intercard_link_downstream elaborate with INTERCARD_BUS_WIDTH = 128 (CLK direction split per ADR-003) and the two-card pair wires up cleanly."
