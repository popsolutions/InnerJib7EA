<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
<!-- Copyright (c) 2026 PopSolutions Cooperative -->

# popsolutions_intercard — KiCad library for the inter-card connector

This directory contains the KiCad 8 symbol and footprint library for the
PopSolutions inter-card link connector specified in:

- [`docs/hw/intercard-connector-pinout.md`](../../docs/hw/intercard-connector-pinout.md) — pinout, electrical targets
- [`docs/adr/0002-intercard-connector.md`](../../docs/adr/0002-intercard-connector.md) — decision rationale

## Files

| File | Purpose |
|---|---|
| `popsolutions_intercard.kicad_sym` | Symbol library (one symbol: `J_INTERCARD_40P`) |
| `popsolutions_intercard.pretty/J_INTERCARD_QSE_40P_0p8mm.kicad_mod` | SMD footprint, 40-pin 0.8 mm pitch dual-row board-to-board |

## Licensing

Per the project SPDX policy:

- **KiCad design files** (`.kicad_sym`, `.kicad_mod`, future `.kicad_sch`,
  `.kicad_pcb`) are licensed under **CERN-OHL-S-2.0**.
  KiCad's sexpr format does not allow embedded SPDX comments without
  breaking the parser, so the license is asserted at the directory level
  via this README and the repository-root `LICENSE` / `NOTICE.md`.
- This README itself is **CC-BY-SA-4.0** (per the docs/markdown SPDX
  policy, declared in the comment on line 1).

## How to consume this library from a KiCad 8 project

In your project's `sym-lib-table` add:

```lisp
(lib (name "popsolutions_intercard")
     (type "KiCad")
     (uri "${KIPRJMOD}/<relative-path>/popsolutions_intercard.kicad_sym")
     (options "")
     (descr "PopSolutions inter-card connector"))
```

In your project's `fp-lib-table` add:

```lisp
(lib (name "popsolutions_intercard")
     (type "KiCad")
     (uri "${KIPRJMOD}/<relative-path>/popsolutions_intercard.pretty")
     (options "")
     (descr "PopSolutions inter-card connector footprints"))
```

For the canonical `Stays/kicad/innerjib7ea-rev-a/` consumer paths, see
the worked snippet in
[`docs/hw/intercard-connector-pinout.md`](../../docs/hw/intercard-connector-pinout.md) §5.3.

## Why this library lives here (not in MAST or Stays)

This library will be promoted to the **MAST trunk** at
`mast/kicad/intercard/` once Stays integrates it and other Sails
(ForeTopsail7EA, MainTopsail7EA) adopt it. It currently lives inside
InnerJib7EA because:

1. Stays's working tree was on a stale feature branch at the time of
   authoring (raising a working-tree collision risk with another agent).
2. InnerJib7EA is the first consumer, so colocating the library with
   its first consumer minimizes coordination friction.

Promotion path: see open follow-up in
[`docs/hw/intercard-connector-pinout.md`](../../docs/hw/intercard-connector-pinout.md) §10.

## Validation

Open the symbol in KiCad 8 (`File → Open → popsolutions_intercard.kicad_sym`)
and the footprint via `File → Open → J_INTERCARD_QSE_40P_0p8mm.kicad_mod`.
Both files use the KiCad 8 sexpr format (`version 20231120` for symbols,
`version 20240108` for footprints).

Authored by hand from the documented pinout and connector datasheet
dimensions (Samtec QSE-040 family, 0.8 mm pitch, body 17.6 mm × 5.5 mm).
