<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
<!-- Copyright (c) 2026 PopSolutions Cooperative -->

# Inter-card connector pinout and PCB footprint (POPC_16A / InnerJib7EA)

**Status:** Draft for review (`popsolutions/InnerJib7EA#8`)
**Stream:** 2 (FPGA Hardware)
**Authored by:** Agent 2 (FPGA Hardware)
**Cross-references:** ADR-002 (this same PR), MAST `interconnect` block (Stream 1),
Spanker scheduler bandwidth model (Stream 3, MAST#18).

## 1. Why this exists

The PopSolutions Sails program has a first-class **multi-card parallelism**
mandate: every Sail PCB must include inter-card connectors *physically
present* even on single-card configurations, so that two-card aggregation
("Sprint H") becomes a soldering exercise, not a board respin.

The original ADR-001 specified an M.2 22110 form factor with no inter-card
link (single-card only, multi-card via host-mediated PCIe peer-to-peer).
The form-factor decision is implemented in the Stays repo (PCB), and Stays
PR #18 amended the form factor to **Mini-ITX SBC with GbE host link**,
which lifts the area constraint that made dedicated inter-card connectors
impractical on M.2. This PR designs the connector that lands on the
rev-A Mini-ITX board.

## 2. Signal budget

The MAST `interconnect` block (Stream 1, in design) targets the
"MAST #14 contract" widths verified by the Spanker scheduler PR #6:

| Parameter            | Value | Rationale                                                |
|----------------------|------:|----------------------------------------------------------|
| `INTERCARD_LANES`    | 4     | One TX-RX pair per lane → 4 simultaneous bidirectional flows. |
| `INTERCARD_LANE_WIDTH` | 32  | 32-bit symbol per beat per lane (matches `xlen`).        |
| `INTERCARD_BUS_WIDTH`  | 128 | 4 × 32 = 128 bits aggregate per direction per beat.      |

The physical layer is **serial differential** per lane (LVDS-class). One
"lane" on the connector is one TX differential pair *and* one RX
differential pair, each carrying serialized 32-bit symbols (e.g., 8b/10b
or 64b/66b — line-coding choice deferred to a later ADR; see open follow-up
in §10).

### 2.1 Per-direction signal count

For each of 4 lanes, per direction:

- 1 differential pair (`P` / `N`) → 2 pins
- 4 lanes × 2 pins = 8 pins per direction
- TX direction + RX direction = **16 pins for data**

Plus shared signals:

- 1 differential clock pair (`CLK_P` / `CLK_N`) → **2 pins**
  (forwarded source-synchronous clock from the upstream card)
- 1 single-ended reset (`RESET_N`) → **1 pin**
  (active-low, asserted by either card to force link re-train)
- 1 single-ended presence-detect (`PRSNT_N`) → **1 pin**
  (downstream card pulls low; upstream sees logic-0 = neighbor present)
- 1 single-ended SMBus / I2C clock + data for slow-path sideband
  (`SMB_CLK`, `SMB_DAT`) → **2 pins**
  (out-of-band link state, board-ID, telemetry — independent of high-speed lanes)

**Subtotal of signal pins:** 16 + 2 + 1 + 1 + 2 = **22 signal pins**.

### 2.2 Power and ground

Decision: **signals only** — connectors do *not* carry power between cards.
Each Sail PCB has its own PSU rail tree (3.3 V / 1.8 V / 1.1 V, fed from
the Mini-ITX 12 V input per ADR-001 amendment). This avoids:

- Inrush current coordination across multiple PSUs.
- A single point of failure in the inter-card link cable / connector.
- Regulatory burden (a power-bearing connector between user-installed cards
  attracts more scrutiny than a signal-only connector).

GND pin count is sized for differential return-current integrity, not
for power delivery. Convention: **1 GND pin between every adjacent
differential pair** for crosstalk isolation, plus 2 GND pins at each
end of the connector for shielding. With 4 TX pairs + 4 RX pairs +
1 CLK pair = 9 differential pairs, that is **9 GND-between + 4 GND-end
= 13 GND pins** (rounding up to keep the ground plane stitched).

### 2.3 Total pin count

22 signal + 13 GND = **35 pins minimum.** Round up to a standard
connector size with margin for future expansion. **Target: 40-pin
connector** (5 spare pins reserved, marked `RSVD` in the pinout below).

## 3. Connector choice

### 3.1 Options evaluated

| Option | Pitch | Density | Mating cycles | Cost / pair | JLCPCB stock | Notes |
|---|---|---|---|---|---|---|
| Samtec QSE-040 / QTE-040 | 0.8 mm | 80-pin (40+40 dual-row) | 100+ | ~USD 4–6 | LCSC carries equivalents | Industrial standard, official KiCad lib from Samtec. |
| Hirose FX23-40S         | 0.5 mm | 40-pin single-row mezzanine | 50  | ~USD 3 | Yes (LCSC C2675473)   | Smaller, lower mating cycles. |
| Hirose DF40C-40DS       | 0.4 mm | 40-pin board-to-board | 30  | ~USD 1.5 | Yes (LCSC C124589)    | Cheapest, but tightest pitch — 4-layer PCB minimum to fan out. |
| 2x20 0.1" header        | 2.54 mm | 40-pin through-hole | many | <USD 0.5 | Yes (LCSC C2845749)   | Cheap and rugged but huge footprint and not high-speed friendly. |

### 3.2 Decision

**Samtec QSE-040-01-L-D-A** (or pin-compatible Hirose FX18 family — both
0.8 mm pitch, dual-row, 40-pin, rated for differential signaling beyond
10 Gbps).

Rationale:

1. **Signal integrity at our target rate.** The MAST link will run at
   roughly 1–2.5 Gbps per lane initially (10 Gbit aggregate after 4-lane
   bonding) — well within QSE-series ratings. The 0.8 mm pitch is the
   sweet spot: tight enough to keep the connector area small, loose
   enough to fan out on a 4-layer PCB without HDI vias.
2. **Mating cycles.** 100+ rated mating cycles is essential because
   developer kits get plugged and unplugged repeatedly during bring-up.
   The DF40 series (30 cycles) is unsuitable.
3. **Open-source ecosystem.** Samtec publishes [official KiCad
   libraries](https://www.samtec.com/products/qse) (S-parameter models,
   3D STEP, KiCad symbol + footprint), removing the multi-day cost of
   authoring a library from datasheet PDFs. This aligns with the project
   memory `project_mission_and_open_fpga_commitment.md` — open-tooling-first.
4. **JLCPCB compatibility.** The **basic-part-equivalent** for the
   Samtec QSE family at JLCPCB is the **Hirose FX18-40P-0.8SH** (LCSC
   C40503) — pin-compatible and roughly half the unit cost (USD 2.50).
   We design the footprint to accept either, calling the part `J_INTERCARD_40P`
   in the schematic.
5. **Power decision compatible.** With signals-only, 0.8 mm pitch is
   plenty of current capacity for the only loads on the connector
   (sideband I2C and pull-ups), even though we do not expect to draw
   meaningful current through it.

### 3.3 Sourcing

- **Primary BOM (rev-A small-batch):** Samtec QSE-040-01-L-D-A —
  Samtec direct sales, ~USD 5/unit qty 10.
- **Cost-down path (rev-B / production):** Hirose FX18-40P-0.8SH —
  LCSC C40503, JLCPCB basic part, ~USD 2.50/unit qty 100.
- **Manual-assembly fallback (lab bring-up only):** 2x20 0.1" header
  (LCSC C2845749) — soldered to the same footprint via an adapter
  daughterboard if neither high-density part is available. Not a
  production option.

## 4. Pinout

40 pins, dual-row (rows A and B, 20 pins per row). Pin numbering follows
KiCad / IPC convention: looking *into* the connector mating face on the
PCB top side, pin 1 is top-left, pin 20 is bottom-left, pin 21 is
bottom-right, pin 40 is top-right.

| Pin | Signal     | Direction | Diff partner | Notes                                         |
|----:|------------|-----------|--------------|-----------------------------------------------|
|   1 | GND        | PWR       | —            | End shield                                     |
|   2 | TX0_P      | OUT       | 3            | Lane 0 transmit positive                       |
|   3 | TX0_N      | OUT       | 2            | Lane 0 transmit negative                       |
|   4 | GND        | PWR       | —            | Crosstalk isolation                            |
|   5 | TX1_P      | OUT       | 6            | Lane 1 transmit positive                       |
|   6 | TX1_N      | OUT       | 5            | Lane 1 transmit negative                       |
|   7 | GND        | PWR       | —            | Crosstalk isolation                            |
|   8 | TX2_P      | OUT       | 9            | Lane 2 transmit positive                       |
|   9 | TX2_N      | OUT       | 8            | Lane 2 transmit negative                       |
|  10 | GND        | PWR       | —            | Crosstalk isolation                            |
|  11 | TX3_P      | OUT       | 12           | Lane 3 transmit positive                       |
|  12 | TX3_N      | OUT       | 11           | Lane 3 transmit negative                       |
|  13 | GND        | PWR       | —            | Crosstalk isolation                            |
|  14 | CLK_P      | OUT       | 15           | Forwarded source-synchronous clock positive    |
|  15 | CLK_N      | OUT       | 14           | Forwarded source-synchronous clock negative    |
|  16 | GND        | PWR       | —            | Clock shielding                                |
|  17 | RESET_N    | I/O       | —            | Active-low link reset (open-drain, pull-up upstream) |
|  18 | PRSNT_N    | IN        | —            | Active-low presence detect (downstream pulls low) |
|  19 | SMB_CLK    | I/O       | —            | Sideband I2C clock (100 kHz default, 3.3 V open-drain) |
|  20 | SMB_DAT    | I/O       | —            | Sideband I2C data                              |
|  21 | GND        | PWR       | —            | End shield (mirror)                            |
|  22 | RX0_P      | IN        | 23           | Lane 0 receive positive                        |
|  23 | RX0_N      | IN        | 22           | Lane 0 receive negative                        |
|  24 | GND        | PWR       | —            | Crosstalk isolation                            |
|  25 | RX1_P      | IN        | 26           | Lane 1 receive positive                        |
|  26 | RX1_N      | IN        | 25           | Lane 1 receive negative                        |
|  27 | GND        | PWR       | —            | Crosstalk isolation                            |
|  28 | RX2_P      | IN        | 29           | Lane 2 receive positive                        |
|  29 | RX2_N      | IN        | 28           | Lane 2 receive negative                        |
|  30 | GND        | PWR       | —            | Crosstalk isolation                            |
|  31 | RX3_P      | IN        | 32           | Lane 3 receive positive                        |
|  32 | RX3_N      | IN        | 31           | Lane 3 receive negative                        |
|  33 | GND        | PWR       | —            | Crosstalk isolation                            |
|  34 | RSVD0      | —         | —            | Reserved (no-connect on rev-A)                 |
|  35 | RSVD1      | —         | —            | Reserved (no-connect on rev-A)                 |
|  36 | GND        | PWR       | —            | Crosstalk isolation                            |
|  37 | RSVD2      | —         | —            | Reserved (no-connect on rev-A)                 |
|  38 | RSVD3      | —         | —            | Reserved (no-connect on rev-A)                 |
|  39 | RSVD4      | —         | —            | Reserved (future second clock pair)            |
|  40 | GND        | PWR       | —            | End shield                                     |

### 4.1 Electrical targets

- **Differential impedance:** 100 Ω ± 10 % on all `*_P` / `*_N` pairs.
- **Single-ended impedance:** 50 Ω on each leg of a differential pair.
- **Maximum trace length on PCB before connector:** 50 mm
  (matched-length groups within 0.5 mm intra-pair, 5 mm inter-pair).
- **ESD protection:** Each high-speed pin requires a low-capacitance
  TVS (≤ 1.5 pF) such as TI TPD2EUSB30 or equivalent. Sideband
  (`SMB_CLK`, `SMB_DAT`, `RESET_N`, `PRSNT_N`) requires standard ESD
  TVS at 6.5 V clamp.
- **Hot-plug:** Not supported on rev-A. Cards must be powered down
  before mating / unmating.

## 5. Footprint and KiCad library

### 5.1 KiCad library identity

- Library: `popsolutions_intercard`
- Symbol: `J_INTERCARD_40P`
- Footprint: `popsolutions_intercard:J_INTERCARD_QSE_40P_0p8mm`
- 3D model: deferred to schematic-capture PR (use Samtec's official STEP
  from samtec.com/3d-models)

### 5.2 Where the files live

This PR places the symbol and footprint **inside the InnerJib7EA repo**
under `kicad/intercard-connector/` because:

1. The Stays repo working tree was on a stale branch
   (`feat/stream-2/pr-XX-kicad-rev-a-bootstrap`) at the time of authoring,
   raising a working-tree collision risk with another agent.
2. Other Sails (ForeTopsail7EA, MainTopsail7EA) will reuse the same
   intercard connector; keeping the canonical KiCad files inside InnerJib7EA
   is fine for now and they will be promoted to the **MAST trunk** at
   `mast/kicad/intercard/` in a follow-up PR (see open follow-ups in §10).

### 5.3 How to consume from Stays (rev-A board project)

In `Stays/kicad/innerjib7ea-rev-a/sym-lib-table`, append a pinned-relative
entry pointing back to InnerJib7EA's MAST submodule mirror, or to a
`Stays/lib/intercard-connector/` symlink. A worked snippet:

```lisp
(sym_lib_table
  (version 7)
  (lib (name "popsolutions_intercard")
       (type "KiCad")
       (uri "${KIPRJMOD}/../../lib/intercard-connector/popsolutions_intercard.kicad_sym")
       (options "")
       (descr "PopSolutions inter-card connector library (mirrored from InnerJib7EA)")))
```

with the analogous entry in `fp-lib-table` pointing at
`popsolutions_intercard.pretty/`.

The symbol file in this PR (`popsolutions_intercard.kicad_sym`) and the
footprint file (`popsolutions_intercard.pretty/J_INTERCARD_QSE_40P_0p8mm.kicad_mod`)
are both **valid KiCad 8 sexpr** and can be opened in KiCad 8 directly
without conversion.

## 6. SystemVerilog port-surface contract

The corresponding RTL stub at `src/intercard_link.sv` declares:

```systemverilog
module intercard_link #(
    parameter int INTERCARD_LANES      = 4,
    parameter int INTERCARD_LANE_WIDTH = 32
)(
    input  wire                          ref_clk,
    input  wire                          rst_n,
    // 4 differential TX pairs (driven out as serial diff symbols)
    output wire [INTERCARD_LANES-1:0]    tx_p,
    output wire [INTERCARD_LANES-1:0]    tx_n,
    // 4 differential RX pairs
    input  wire [INTERCARD_LANES-1:0]    rx_p,
    input  wire [INTERCARD_LANES-1:0]    rx_n,
    // Forwarded clock
    output wire                          clk_p,
    output wire                          clk_n,
    // Sideband
    input  wire                          prsnt_n,
    inout  wire                          reset_n,
    inout  wire                          smb_clk,
    inout  wire                          smb_dat
);
```

This stub has no body in this PR (it is a port-surface contract, not a
transceiver implementation). The real transceiver and 8b/10b PCS land
in a separate PR after the intercard line-coding ADR.

The bus width contract `INTERCARD_BUS_WIDTH = INTERCARD_LANES * INTERCARD_LANE_WIDTH = 128`
is asserted by the smoke-test in `verif/intercard_link/`.

## 7. Validation in this PR

- `verilator --lint-only` over `src/intercard_link.sv` confirms the
  module elaborates with the expected widths. Driver script:
  `verif/intercard_link/run_lint.sh`.
- Width contract assertion in `verif/intercard_link/test_widths.sv`:
  generates an elaboration-time `$error` if
  `INTERCARD_LANES * INTERCARD_LANE_WIDTH != 128`.

## 8. Out of scope

- Actual placement on the PCB layout (Stays issue #10).
- Controlled-impedance stackup choice (Stays issue #9).
- 8b/10b vs 64b/66b line coding (separate ADR, depends on MAST#14).
- Schematic capture of the FPGA-side intercard transceiver (separate PR
  on the InnerJib7EA repo, follows ADR-014 in MAST).
- Electrical bring-up testbench (Sprint H deliverable).

## 9. Cross-stream impact

| Stream | Impact | Action |
|---|---|---|
| 1 (RTL) | The `intercard_link` module port surface is the contract that the MAST `interconnect` block wraps. | Issue filed in MAST repo: cross-stream coordination. |
| 3 (Spanker) | Bandwidth model: 4 lanes × ~1.25 Gbps = ~5 Gbps aggregate per direction = ~625 MB/s per direction (8b/10b). Spanker's TP/MP scheduler uses this number. | Issue filed in Spanker repo: please assert against this number. |
| 4 (Upstream) | None — this connector predates any upstream Litex/LiteEth work. | No action. |

## 10. Open follow-ups

- ADR-014 in MAST: line coding choice (8b/10b vs 64b/66b vs SerDes IP).
- Promote `kicad/intercard-connector/` from InnerJib7EA → MAST trunk
  once Stays integrates.
- Schematic capture of FPGA-side intercard transceiver.
- Power-tree update: confirm the 13 GND pins do not raise the inrush
  current envelope at PSU power-on (signals-only, but the GND plane
  is now bonded between cards via the connector).
- Hot-plug capability for rev-B (warm-swap of failed cards in a
  multi-card bench).
