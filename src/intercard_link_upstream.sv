// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 PopSolutions Cooperative
//
// intercard_link_upstream — port-surface contract for the InnerJib7EA
// inter-card link, **upstream-card role** (clock-forwarding side).
//
// Role:
//   This module models a card that is the SOURCE of the forwarded
//   source-synchronous clock on the inter-card connector — i.e., it
//   DRIVES `clk_p`/`clk_n` out to the connector.
//
//   The downstream-card role (which CONSUMES the clock as an input)
//   lives in src/intercard_link_downstream.sv. The two roles share
//   the same connector pinout — only the CLK pair direction flips,
//   per docs/hw/intercard-connector-pinout.md §2.1 §6 and ADR-003.
//
// This module is a STUB. It declares the port surface that physically
// maps to the 40-pin board-to-board connector specified in:
//
//   docs/hw/intercard-connector-pinout.md   — pinout, electrical targets
//   docs/adr/0002-intercard-connector.md    — connector decision rationale
//   docs/adr/0003-intercard-link-role-split.md — upstream/downstream split
//
// The body of this module (transceiver, 8b/10b PCS, link bring-up FSM,
// AXI4-Stream upstream interface) is NOT implemented in this PR. It will
// land in a follow-up PR after the line-coding ADR (MAST ADR-014) lands.
//
// The width contract this stub establishes is asserted at elaboration time
// by verif/intercard_link/test_widths.sv.
//
// Cross-stream contracts:
//   - MAST issue #14 ("interconnect" block port-surface contract)
//   - Spanker PR #6 ("MAST #14 contract" bandwidth model)
//
// Tooling: SystemVerilog 2012; tested with Verilator 5.x in --lint-only
// mode. iverilog -g2012 also accepted.

`default_nettype none

module intercard_link_upstream #(
    // Width contract — see docs/hw/intercard-connector-pinout.md §2.
    // INTERCARD_LANES * INTERCARD_LANE_WIDTH must equal 128 (the
    // INTERCARD_BUS_WIDTH of the MAST #14 contract).
    parameter int INTERCARD_LANES      = 4,
    parameter int INTERCARD_LANE_WIDTH = 32
)(
    // --- Reference clock / reset (from on-card PLL, NOT from connector) ---
    input  wire                        ref_clk,
    input  wire                        rst_n,

    // --- High-speed differential transmit pairs (4 lanes) ---
    // Each lane carries serialized 32-bit symbols. Mapped to connector
    // pins TX0_P/N (2/3), TX1_P/N (5/6), TX2_P/N (8/9), TX3_P/N (11/12).
    output wire [INTERCARD_LANES-1:0]  tx_p,
    output wire [INTERCARD_LANES-1:0]  tx_n,

    // --- High-speed differential receive pairs (4 lanes) ---
    // Mapped to connector pins RX0_P/N (22/23), RX1_P/N (25/26),
    // RX2_P/N (28/29), RX3_P/N (31/32).
    input  wire [INTERCARD_LANES-1:0]  rx_p,
    input  wire [INTERCARD_LANES-1:0]  rx_n,

    // --- Forwarded source-synchronous clock differential pair ---
    // UPSTREAM ROLE: this card DRIVES the clock out to the connector
    // (pins CLK_P (14), CLK_N (15)). The downstream-card pad strap is
    // an input that recovers this clock for RX time alignment.
    output wire                        clk_p,
    output wire                        clk_n,

    // --- Sideband single-ended ---
    // PRSNT_N (pin 18): downstream card pulls this low; upstream card
    // sees logic-0 = neighbor present. Pure input on this card.
    input  wire                        prsnt_n,

    // RESET_N (pin 17): open-drain, bidirectional. Either card can
    // assert (drive low) to force a link re-train.
    inout  wire                        reset_n,

    // SMB_CLK / SMB_DAT (pins 19/20): I2C/SMBus sideband for slow-path
    // telemetry, board ID, link state. Standard 100 kHz, 3.3 V open-drain.
    inout  wire                        smb_clk,
    inout  wire                        smb_dat
);

    // ------------------------------------------------------------------
    // Width-contract sanity: INTERCARD_LANES * INTERCARD_LANE_WIDTH must
    // equal 128 (INTERCARD_BUS_WIDTH per the MAST #14 contract). Any
    // override that breaks this contract will fail elaboration.
    //
    // NOTE on placement: $error sits directly in the generate body (NOT
    // wrapped in `initial begin ... end`). Verilator `--lint-only` parses
    // and elaborates the design but does NOT run `initial` blocks, so
    // wrapping $error in `initial` would mask a contract violation under
    // lint-only (issue #12). Generate-body $error is an IEEE 1800-2012
    // elaboration-time construct and is enforced by Verilator at lint time.
    // ------------------------------------------------------------------
    localparam int INTERCARD_BUS_WIDTH = INTERCARD_LANES * INTERCARD_LANE_WIDTH;

    generate
        if (INTERCARD_BUS_WIDTH != 128) begin : g_width_contract_broken
            $error("intercard_link_upstream: INTERCARD_LANES (%0d) * INTERCARD_LANE_WIDTH (%0d) = %0d, expected 128 (MAST #14 contract).",
                   INTERCARD_LANES, INTERCARD_LANE_WIDTH, INTERCARD_BUS_WIDTH);
        end
    endgenerate

    // ------------------------------------------------------------------
    // Stub body: tie outputs to safe defaults so synthesis/elab does not
    // warn about unconnected drivers. The real transceiver replaces this
    // with the SerDes + 8b/10b PCS + AXI4-Stream upstream.
    // ------------------------------------------------------------------
    assign tx_p  = '0;
    assign tx_n  = '1;        // diff complement of tx_p
    assign clk_p = ref_clk;
    assign clk_n = ~ref_clk;

    // High-Z on bidirectional sideband until the link FSM is implemented.
    assign reset_n = 1'bz;
    assign smb_clk = 1'bz;
    assign smb_dat = 1'bz;

    // Suppress unused-input lint by tying off in a synthesizable no-op.
    /* verilator lint_off UNUSED */
    wire _unused = &{1'b0, rx_p, rx_n, prsnt_n, rst_n};
    /* verilator lint_on UNUSED */

endmodule

`default_nettype wire
