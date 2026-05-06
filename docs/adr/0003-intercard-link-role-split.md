<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
<!-- Copyright (c) 2026 PopSolutions Cooperative -->

# ADR-003 — Inter-card link role split (upstream / downstream)

**Status:** Accepted (2026-05-06)

**Closes:** `popsolutions/InnerJib7EA#13`

**Supersedes (in part):** the single-module port-surface contract introduced
by `popsolutions/InnerJib7EA#11` (`src/intercard_link.sv`), refined by
`popsolutions/InnerJib7EA#14`. This ADR splits that single module into
two role-specific variants without changing the connector pinout, the
width contract, or the lane count.

## Context

PR #11 introduced `src/intercard_link.sv`, a port-surface stub for the
40-pin board-to-board inter-card connector specified in
[`docs/hw/intercard-connector-pinout.md`](../hw/intercard-connector-pinout.md)
and decided in [ADR-002](0002-intercard-connector.md). PR #14 hardened
the elaboration-time width-contract guard.

Both PRs declared the forwarded-clock pair `clk_p` / `clk_n` as
**unconditionally `output`** on the module port surface:

```systemverilog
// src/intercard_link.sv (pre-ADR-003)
output wire                        clk_p,
output wire                        clk_n,
```

The pinout document, however, describes CLK as a *forwarded
source-synchronous clock from the upstream card* (§2.1, §6). Two cards
that mate via this connector occupy different roles:

- The **upstream card** drives the CLK pair *out* to the connector.
- The **downstream card** consumes the CLK pair *in* from the connector
  and uses the recovered clock to time-align its RX serializer.

A single module with `clk_p` / `clk_n` declared `output` only models the
upstream-card role. A downstream-card instantiation (which physically
needs CLK as `input`) would not compile against that port surface. The
issue body for `popsolutions/InnerJib7EA#13` flagged this gap as a
medium-severity finding from the Agent R review of PR #11.

The connector pinout itself does not change: pin 14 is `CLK_P`, pin 15
is `CLK_N` regardless of role. Only the *direction* of the FPGA pad
strap varies per role.

## Decision

**Adopt Option C: rename the existing module to
`intercard_link_upstream`, and add a parallel `intercard_link_downstream`
module with CLK declared as input.**

The two modules:

- **Share** all parameters (`INTERCARD_LANES`, `INTERCARD_LANE_WIDTH`),
  the width contract (`INTERCARD_BUS_WIDTH = 128`, MAST #14), and the
  set of port names.
- **Differ** in CLK direction (`output` vs `input`) and in
  `prsnt_n` direction (`input` on upstream — observes neighbour's
  pull-down; `output` on downstream — drives the pull-down).
- Are both stubs in this PR. The transceiver body, line coding (8b/10b
  vs 64b/66b — see ADR-014 in MAST), and AXI4-Stream upstream interface
  all land in a follow-up PR.

The renaming uses `git mv` so blame history on `intercard_link.sv`
is preserved on `intercard_link_upstream.sv`.

### File layout after this ADR

```
src/intercard_link_upstream.sv     - clk_p/clk_n OUTPUT, prsnt_n INPUT
src/intercard_link_downstream.sv   - clk_p/clk_n INPUT,  prsnt_n OUTPUT
verif/intercard_link/test_widths.sv          - instantiates both
verif/intercard_link/test_two_card_pair.sv   - wires up to dn, structural CLK assertion
verif/intercard_link/run_lint.sh             - lints both top-modules
```

## Alternatives considered

### Option A — single module with a `CARD_ROLE` parameter

```systemverilog
module intercard_link #(
    parameter string CARD_ROLE = "UPSTREAM"  // or "DOWNSTREAM"
) (
    // ...
);
```

A `generate` block would conditionally declare `clk_p` / `clk_n` as
`output` or `input` based on `CARD_ROLE`.

**Rejected** because:

1. SystemVerilog 2012 does not allow port direction to be selected by a
   `generate`-time elaboration parameter. Achieving Option A requires a
   *wrapper* module per role, and the wrapper would import the
   inner-module ports with their fixed direction — at which point the
   wrapper IS Option B / C with extra indirection.
2. Tooling-portability risk: even with a wrapper, downstream lint
   (Verilator, iverilog, vendor SV elaborators) treats parameter-driven
   port direction inconsistently. The Sails program targets the open
   FPGA ecosystem first (`project_mission_and_open_fpga_commitment.md`),
   where tooling diversity is a feature, not a bug, and ambiguity in
   the port surface is a tax we cannot afford.
3. Call-site readability suffers: callers have to know to pass
   `CARD_ROLE("UPSTREAM")` correctly, with no compile-time defence
   against the wrong choice. With Option C the wrong choice is a
   missing module reference, which any synthesizer rejects immediately.

### Option B — two modules sharing logic via a `*_core` private module

`intercard_link_upstream` and `intercard_link_downstream` both wrap a
shared `intercard_link_core` private module that holds the body
(transceiver, FSM, etc.).

**Rejected for this PR, deferred for the transceiver-body PR.** The
modules in this PR are STUBS — there is no body to share yet, and
forcing a `_core` indirection on three nearly-empty stub bodies is
premature factoring (YAGNI). When the transceiver body lands, its PR
can introduce the `_core` extraction if duplication actually shows up.
The split this ADR performs does not foreclose that future move; it
sets up the public surface that any future `_core` extraction would
have to expose anyway.

### Option C — rename existing module to `intercard_link_upstream`, add new `intercard_link_downstream` (CHOSEN)

**Accepted.** Smallest disruption from PR #11 / #14:

- Existing module's logic is preserved verbatim — only the file name and
  `module` identifier change.
- Existing testbench logic is preserved — only the instance name and
  the `module` reference change.
- Each module has a clean, self-describing port surface.
- Two-card-pair elaboration test (`test_two_card_pair.sv`) wires the
  upstream's CLK output directly into the downstream's CLK input via a
  single shared `wire`, making the CLK-direction contract a structural
  property enforced by Verilator's multi-driver / undriven-output
  checks.

### "Leave it ambiguous" — non-option

Keeping `intercard_link.sv` with CLK unconditionally output, and adding
a comment that the receiver-side card has to "wrap and flip" the CLK
direction, was considered as a no-op. It is rejected because:

1. The "wrap and flip" RTL would have to live somewhere. With Option C,
   that "somewhere" is a first-class module that gets the same lint and
   test coverage as the upstream variant. With the no-op, every
   downstream call site has to re-implement the wrapper, multiplying
   the surface area for direction-bug regressions.
2. The ambiguity itself was the finding raised in
   `popsolutions/InnerJib7EA#13`. Closing the issue requires removing
   the ambiguity from the port surface, not papering over it.

## Consequences

### Positive

- Each role has a self-describing module name; misuse manifests at
  elaboration time, not at PCB integration time.
- The two-card-pair elaboration test
  (`verif/intercard_link/test_two_card_pair.sv`) gives Stream 2 a
  CI-enforced structural proof of the CLK direction contract — every
  PR that touches either module has to pass `run_lint.sh`.
- Connector pinout is unchanged. The KiCad symbol & footprint
  (`kicad/intercard-connector/popsolutions_intercard.kicad_sym` and
  `popsolutions_intercard.pretty/`) are unaffected.

### Negative

- Two SV files to maintain instead of one. The bodies are still stubs;
  the duplication cost is small. When the transceiver body lands,
  ADR-003 invites a follow-up to extract the shared logic per Option B.
- Future top-level integrations (e.g., `inner_jib_top.sv`, `gpu_die.sv`
  in MAST) will need to instantiate the role-appropriate variant. The
  current `inner_jib_top.sv` does not yet instantiate any intercard
  module, so this PR does not break any call site.

### Downstream caller impact

| Caller (planned)                       | Module to instantiate          |
|----------------------------------------|--------------------------------|
| `inner_jib_top.sv` upstream-card build | `intercard_link_upstream`      |
| `inner_jib_top.sv` downstream build    | `intercard_link_downstream`    |
| MAST `gpu_die.sv` upstream slot        | `intercard_link_upstream`      |
| MAST `gpu_die.sv` downstream slot      | `intercard_link_downstream`    |

No call sites today instantiate either module — the integration work
lands in a follow-up PR after the transceiver body. The choice between
upstream and downstream at integration time is a board-strap / SKU
decision (which PCB position the FPGA occupies in a multi-card stack).

### Deferred to follow-up ADRs / PRs

- **Transceiver body** — SerDes + 8b/10b PCS + AXI4-Stream upstream
  interface. Depends on MAST ADR-014 (line coding).
- **Shared core extraction** (Option B refactor) — only worthwhile once
  the transceiver body shows real duplication.
- **Power-good gating of `prsnt_n`** — currently the downstream module
  ties `prsnt_n` to `1'b0`; the real implementation will gate it from
  the on-card power-good signal.
- **`reset_n` open-drain semantics** — both roles model `reset_n` as
  bidi `inout` with high-Z; the actual pull-up + assert-low driver
  arbitration lands with the link-bring-up FSM PR.

## Verification in this PR

- `verif/intercard_link/test_widths.sv` instantiates both
  `intercard_link_upstream u_upstream` and
  `intercard_link_downstream u_downstream` in the same elaboration
  unit. Verilator `--lint-only` on this file proves both modules have
  consistent and self-consistent port surfaces.
- `verif/intercard_link/test_two_card_pair.sv` cross-wires the
  upstream's TX/CLK outputs into the downstream's RX/CLK inputs (and
  vice versa for downstream-to-upstream RX). Elaboration passes only
  if every cross-wired net has exactly one driver and one or more
  consumers — this is the structural CLK-direction assertion.
- `verif/intercard_link/run_lint.sh` runs both Verilator passes and
  exits 0 on combined success.

A representative successful run on Verilator 5.048 reports:

```
[run_lint] (1/2) widths: ...
[run_lint] (2/2) two-card pair: ...
[run_lint] PASS - intercard_link_upstream + intercard_link_downstream
elaborate with INTERCARD_BUS_WIDTH = 128 (CLK direction split per ADR-003)
and the two-card pair wires up cleanly.
```

A sanity check (manually flipping the downstream's `clk_p` / `clk_n`
from `input` back to `output`) was performed locally: Verilator failed
elaboration with `%Warning-UNDRIVEN: ... 'clk_p'`, confirming the test
catches the regression mode this ADR was written to prevent.

## References

- `docs/adr/0001-spec.md` — locked POPC_16A specification
- `docs/adr/0002-intercard-connector.md` — connector physical decision
- `docs/hw/intercard-connector-pinout.md` — pinout, electrical targets,
  KiCad library identity (updated by this PR to tie CLK direction
  to role explicitly)
- `popsolutions/InnerJib7EA#11` — original `intercard_link.sv` stub
- `popsolutions/InnerJib7EA#12` — width-guard elaboration-time fix
- `popsolutions/InnerJib7EA#14` — width-guard fix landed
- `popsolutions/InnerJib7EA#13` — this issue (CLK direction split)
- Project memory: `project_multicard_parallelism.md` — first-class
  multi-card mandate that motivates having BOTH role variants
  available on every PCB.
- Project memory: `project_mission_and_open_fpga_commitment.md` —
  open-tooling-first stance that rules out parameter-driven port
  direction (Option A).
