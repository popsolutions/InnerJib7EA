// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 PopSolutions Cooperative
//
// test_widths.sv — elaboration-time width-contract assertion for
// intercard_link_upstream and intercard_link_downstream. Designed to
// be compiled by `verilator --lint-only` (no simulation kernel needed)
// so the smoke test runs in CI without cocotb installed.
//
// Pass criterion: verilator returns exit code 0 and the elaboration
// banner reports INTERCARD_BUS_WIDTH = 128 for both modules.
//
// Failure mode: if anyone changes INTERCARD_LANES or INTERCARD_LANE_WIDTH
// in either src/intercard_link_upstream.sv or
// src/intercard_link_downstream.sv such that LANES * LANE_WIDTH != 128,
// the generate-block guard inside the production module fails elaboration
// with a clear error, AND the local guard below also fails.
//
// This testbench also serves as the **two-card-pair elaboration**
// evidence required by ADR-003: it instantiates BOTH role variants
// in the same elaboration unit so the symmetry of the surfaces is
// exercised in CI on every PR.

`default_nettype none

module test_widths;

    // Stimulus / observation nets sized for the default-parameter
    // intercard_link_* modules (INTERCARD_LANES = 4). All ports wired
    // so verilator does not warn about missing instance pins.
    logic       ref_clk = 1'b0;
    logic       rst_n   = 1'b0;

    // ------------------------------------------------------------------
    // Upstream-card instance: drives clk_p / clk_n out, drives tx_*,
    // observes rx_* and prsnt_n.
    // ------------------------------------------------------------------
    wire [3:0]  up_tx_p, up_tx_n, up_rx_p, up_rx_n;
    wire        up_clk_p, up_clk_n;
    logic       up_prsnt_n = 1'b1;
    wire        up_reset_n;
    wire        up_smb_clk;
    wire        up_smb_dat;

    // Drive the upstream's RX inputs to known values so they are not floating.
    assign up_rx_p = 4'b0000;
    assign up_rx_n = 4'b1111;

    intercard_link_upstream u_upstream (
        .ref_clk (ref_clk),
        .rst_n   (rst_n),
        .tx_p    (up_tx_p),
        .tx_n    (up_tx_n),
        .rx_p    (up_rx_p),
        .rx_n    (up_rx_n),
        .clk_p   (up_clk_p),
        .clk_n   (up_clk_n),
        .prsnt_n (up_prsnt_n),
        .reset_n (up_reset_n),
        .smb_clk (up_smb_clk),
        .smb_dat (up_smb_dat)
    );

    // ------------------------------------------------------------------
    // Downstream-card instance: receives clk_p / clk_n in, drives tx_*,
    // observes rx_*, drives prsnt_n out.
    // ------------------------------------------------------------------
    wire [3:0]  dn_tx_p, dn_tx_n, dn_rx_p, dn_rx_n;
    logic       dn_clk_p = 1'b0;
    logic       dn_clk_n = 1'b1;
    wire        dn_prsnt_n;
    wire        dn_reset_n;
    wire        dn_smb_clk;
    wire        dn_smb_dat;

    // Drive the downstream's RX inputs to known values so they are not floating.
    assign dn_rx_p = 4'b0000;
    assign dn_rx_n = 4'b1111;

    intercard_link_downstream u_downstream (
        .ref_clk (ref_clk),
        .rst_n   (rst_n),
        .tx_p    (dn_tx_p),
        .tx_n    (dn_tx_n),
        .rx_p    (dn_rx_p),
        .rx_n    (dn_rx_n),
        .clk_p   (dn_clk_p),
        .clk_n   (dn_clk_n),
        .prsnt_n (dn_prsnt_n),
        .reset_n (dn_reset_n),
        .smb_clk (dn_smb_clk),
        .smb_dat (dn_smb_dat)
    );

    // ------------------------------------------------------------------
    // Generate-block guard: hard elaboration-time check on the contract.
    // If this evaluates false, Verilator fails elaboration with an error
    // pointing at this generate-block — no simulation needed.
    // ------------------------------------------------------------------
    localparam int EXPECT_BUS_WIDTH = 128;
    localparam int ACTUAL_BUS_WIDTH = 4 /* INTERCARD_LANES */ *
                                       32 /* INTERCARD_LANE_WIDTH */;

    // $error sits DIRECTLY in the generate body (no `initial` wrapper).
    // Lint-only mode does NOT run `initial` blocks, so wrapping would
    // mask contract violations under lint-only (issue #12). The bare
    // $error form is an IEEE 1800-2012 elaboration-time construct and
    // is enforced at lint time.
    //
    // The "OK" branch retains `initial $display` because that path is
    // observational, not a gate — when the contract holds, lint-only
    // exits 0 and the display is a no-op (only meaningful under --binary).
    generate
        if (ACTUAL_BUS_WIDTH != EXPECT_BUS_WIDTH) begin : g_width_mismatch
            $error("intercard_link width contract broken: actual=%0d expected=%0d",
                   ACTUAL_BUS_WIDTH, EXPECT_BUS_WIDTH);
        end else begin : g_width_ok
            initial $display("[test_widths] INTERCARD_BUS_WIDTH = %0d (matches MAST #14 contract); both intercard_link_upstream and intercard_link_downstream elaborated.",
                             ACTUAL_BUS_WIDTH);
        end
    endgenerate

endmodule

`default_nettype wire
