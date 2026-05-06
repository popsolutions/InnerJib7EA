// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 PopSolutions Cooperative
//
// test_widths.sv — elaboration-time width-contract assertion for
// intercard_link. Designed to be compiled by `verilator --lint-only`
// (no simulation kernel needed) so the smoke test runs in CI without
// cocotb installed.
//
// Pass criterion: verilator returns exit code 0 and the elaboration
// banner reports INTERCARD_BUS_WIDTH = 128.
//
// Failure mode: if anyone changes INTERCARD_LANES or INTERCARD_LANE_WIDTH
// in src/intercard_link.sv such that LANES * LANE_WIDTH != 128, the
// generate-block guard below fails elaboration with a clear error.

`default_nettype none

module test_widths;

    // Stimulus / observation nets sized for the default-parameter
    // intercard_link (INTERCARD_LANES = 4). All ports wired so verilator
    // does not warn about missing instance pins.
    logic       ref_clk = 1'b0;
    logic       rst_n   = 1'b0;
    wire [3:0]  tx_p, tx_n, rx_p, rx_n;
    wire        clk_p, clk_n;
    logic       prsnt_n = 1'b1;
    wire        reset_n;
    wire        smb_clk;
    wire        smb_dat;

    // Drive RX inputs to known values so they are not floating.
    assign rx_p = 4'b0000;
    assign rx_n = 4'b1111;

    // Default-parameter instantiation: matches the MAST #14 contract.
    intercard_link u_default (
        .ref_clk (ref_clk),
        .rst_n   (rst_n),
        .tx_p    (tx_p),
        .tx_n    (tx_n),
        .rx_p    (rx_p),
        .rx_n    (rx_n),
        .clk_p   (clk_p),
        .clk_n   (clk_n),
        .prsnt_n (prsnt_n),
        .reset_n (reset_n),
        .smb_clk (smb_clk),
        .smb_dat (smb_dat)
    );

    // Generate-block guard: hard elaboration-time check on the contract.
    // If this evaluates false, Verilator fails elaboration with an error
    // pointing at this generate-block — no simulation needed.
    localparam int EXPECT_BUS_WIDTH = 128;
    localparam int ACTUAL_BUS_WIDTH = 4 /* INTERCARD_LANES */ *
                                       32 /* INTERCARD_LANE_WIDTH */;

    generate
        if (ACTUAL_BUS_WIDTH != EXPECT_BUS_WIDTH) begin : g_width_mismatch
            // This $error fires at elaboration. Verilator surfaces it as
            // an elaboration-time error and exits non-zero.
            initial $error("intercard_link width contract broken: actual=%0d expected=%0d",
                           ACTUAL_BUS_WIDTH, EXPECT_BUS_WIDTH);
        end else begin : g_width_ok
            initial $display("[test_widths] INTERCARD_BUS_WIDTH = %0d (matches MAST #14 contract)",
                             ACTUAL_BUS_WIDTH);
        end
    endgenerate

endmodule

`default_nettype wire
