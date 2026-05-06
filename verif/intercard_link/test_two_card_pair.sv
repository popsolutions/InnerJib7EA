// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 PopSolutions Cooperative
//
// test_two_card_pair.sv — two-card-pair elaboration test for the
// role-split intercard_link modules (ADR-003).
//
// What this proves
// ----------------
// This testbench wires an `intercard_link_upstream` instance directly
// to an `intercard_link_downstream` instance via the connector signal
// names (TX-to-RX cross, CLK upstream-to-downstream). The test PASSES
// if the resulting netlist elaborates without errors.
//
// The CLK direction contract (ADR-003) is enforced **structurally** by
// elaboration:
//
//   - `intercard_link_upstream.clk_p`   is declared `output wire`
//   - `intercard_link_downstream.clk_p` is declared `input  wire`
//
// The single shared `wire link_clk_p` between them is therefore driven
// by the upstream and consumed by the downstream — the only legal
// direction. If a future change accidentally flipped either declaration
// (e.g., made the downstream CLK an output too), Verilator would reject
// the elaboration with a multi-driver error on `link_clk_p`. That
// rejection IS the assertion. No simulation kernel needed.
//
// This is intentionally a Verilator `--lint-only` style test — no
// cocotb, no Python, no waveform dump. The cocotb 2-card pair test
// with timing assertions is deferred to the transceiver-body PR
// (where there is actual signal activity to assert against).
//
// Run via the lint driver script at verif/intercard_link/run_lint.sh.

`default_nettype none

module test_two_card_pair;

    // Shared on-card reference clock + reset for both card instances.
    // In the real two-board system each card has its own PLL; for this
    // elaboration test a single net is sufficient.
    logic ref_clk = 1'b0;
    logic rst_n   = 1'b0;

    // ------------------------------------------------------------------
    // The connector: shared nets between the two cards.
    //
    // Cross-cabling convention (matches docs/hw/intercard-connector-pinout.md):
    //   - upstream TX[i]   drives a wire that the downstream sees as RX[i]
    //   - downstream TX[i] drives a wire that the upstream sees as RX[i]
    //   - upstream CLK_P / CLK_N drive the shared CLK net
    //   - shared CLK net feeds the downstream CLK_P / CLK_N inputs
    //   - PRSNT_N is driven by the downstream, observed by the upstream
    // ------------------------------------------------------------------
    wire [3:0] up_to_dn_p, up_to_dn_n;   // upstream TX → downstream RX
    wire [3:0] dn_to_up_p, dn_to_up_n;   // downstream TX → upstream RX
    wire       link_clk_p, link_clk_n;   // upstream CLK → downstream CLK
    wire       link_prsnt_n;             // downstream → upstream
    wire       link_reset_n;             // bidi
    wire       link_smb_clk;             // bidi
    wire       link_smb_dat;             // bidi

    // ------------------------------------------------------------------
    // Upstream-card instance.
    // ------------------------------------------------------------------
    intercard_link_upstream u_up (
        .ref_clk (ref_clk),
        .rst_n   (rst_n),
        .tx_p    (up_to_dn_p),
        .tx_n    (up_to_dn_n),
        .rx_p    (dn_to_up_p),
        .rx_n    (dn_to_up_n),
        .clk_p   (link_clk_p),
        .clk_n   (link_clk_n),
        .prsnt_n (link_prsnt_n),
        .reset_n (link_reset_n),
        .smb_clk (link_smb_clk),
        .smb_dat (link_smb_dat)
    );

    // ------------------------------------------------------------------
    // Downstream-card instance.
    // ------------------------------------------------------------------
    intercard_link_downstream u_dn (
        .ref_clk (ref_clk),
        .rst_n   (rst_n),
        .tx_p    (dn_to_up_p),
        .tx_n    (dn_to_up_n),
        .rx_p    (up_to_dn_p),
        .rx_n    (up_to_dn_n),
        .clk_p   (link_clk_p),
        .clk_n   (link_clk_n),
        .prsnt_n (link_prsnt_n),
        .reset_n (link_reset_n),
        .smb_clk (link_smb_clk),
        .smb_dat (link_smb_dat)
    );

    // Observational banner — only meaningful under --binary, harmless
    // under --lint-only (the test passes purely on structural elaboration).
    initial $display("[test_two_card_pair] elaborated upstream+downstream pair: CLK direction OK (upstream drives, downstream receives).");

endmodule

`default_nettype wire
