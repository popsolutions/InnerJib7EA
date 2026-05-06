<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
<!-- Copyright (c) 2026 PopSolutions Cooperative -->

# ADR-002 — Inter-card connector for InnerJib7EA / POPC_16A

**Status:** Accepted (2026-05-06) — supersedes the "**No NVLink-equivalent.
No inter-card link in Gen A; multi-card scenarios fall back to PCIe
peer-to-peer.**" clause of ADR-001 §Host-interface (line 52–53). Note that
the *companion* form-factor amendment (M.2 → Mini-ITX) lives on the Stays
repo side — see Stays PR #18 — and provides the board area that makes a
dedicated inter-card connector physically practical.

**Closes:** `popsolutions/InnerJib7EA#8`

## Context

The PopSolutions Sails program has a first-class **multi-card parallelism
mandate** (see project memory `project_multicard_parallelism.md`). Every
Sail PCB must carry inter-card connectors *physically present* even on
single-card configurations, so two-card aggregation does not require a
PCB respin.

ADR-001 originally locked the InnerJib7EA host link to PCIe Gen4 x4 on M.2
22110 form factor with no inter-card link. The form-factor decision is
implemented on the PCB-side repo (Stays), and Stays PR #18 amended the
form factor on that side to **Mini-ITX SBC + GbE host link**, which
lifts the area constraint that made dedicated inter-card connectors
impractical on M.2.

This ADR fills the resulting gap: which physical connector lands on the
rev-A board for inter-card signaling.

## Decision

Adopt a **40-pin, 0.8 mm pitch, dual-row board-to-board mezzanine
connector** of the **Samtec QSE-040** family (or pin-compatible
**Hirose FX18-40P-0.8SH** — JLCPCB basic part LCSC C40503).

The connector carries:

- 4 differential transmit pairs (`TX[3:0]_P/N`)
- 4 differential receive pairs (`RX[3:0]_P/N`)
- 1 forwarded-clock differential pair (`CLK_P/N`)
- 4 sideband single-ended pins (`RESET_N`, `PRSNT_N`, `SMB_CLK`, `SMB_DAT`)
- 13 GND pins (1 between each diff pair + 4 end-shield)
- 5 reserved pins for future expansion

**No power between cards.** Each Sail has its own PSU rail tree.

Full per-pin assignment, electrical targets, and KiCad library identity:
see [`docs/hw/intercard-connector-pinout.md`](../hw/intercard-connector-pinout.md).

## Consequences

### Positive

- Two-card "Sprint H" demo becomes a soldering exercise on the same PCB.
- Width contract aligns with MAST `interconnect` block design
  (`INTERCARD_LANES=4`, `INTERCARD_LANE_WIDTH=32`,
  `INTERCARD_BUS_WIDTH=128`), enabling Spanker scheduler bandwidth
  modeling to start immediately.
- Connector choice (Samtec QSE / Hirose FX18) has open KiCad
  libraries published by the manufacturer — no datasheet-to-symbol
  reverse engineering needed.
- Cost path defined: USD 5 (Samtec, low qty) → USD 2.50 (Hirose, JLCPCB
  basic part at qty 100) → 2x20 0.1" header (USD 0.50, lab-only fallback).

### Negative

- Adds ~USD 5 to the BOM at low quantity (within the R$ 800–1500 BOM
  envelope from ADR-001 §BOM target).
- Adds ~12 mm × 8 mm of board area for the connector itself plus
  fan-out keep-out region.
- Bonds the GND planes of both cards once mated — a power-tree
  inrush analysis is required before powering up two cards
  simultaneously (open follow-up).

### Deferred to follow-up ADRs / PRs

- **Line coding** (8b/10b vs 64b/66b vs vendor SerDes IP) — depends on
  MAST ADR-014 (link architecture).
- **Hot-plug capability** — rev-A is power-down-before-mate.
- **Promote KiCad library to MAST trunk** — currently lives in
  InnerJib7EA `kicad/intercard-connector/`; promote once Stays
  integrates and other Sails (ForeTopsail7EA, MainTopsail7EA) reuse.
- **Schematic capture of FPGA-side transceiver** — separate PR.
- **PCB layout placement** — Stays issue #10.
- **Controlled-impedance stackup** — Stays issue #9.

## References

- `docs/hw/intercard-connector-pinout.md` — pinout, electrical, footprint
- `docs/adr/0001-spec.md` — locked POPC_16A specification (amended PR #18)
- Project memory: `project_multicard_parallelism.md`
- MAST issue #14 — `interconnect` block port-surface contract
- Spanker PR #6 — bandwidth assertion against the MAST #14 contract
