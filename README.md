<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# InnerJib7EA — POPC_16A

> First Sail of the PopSolutions fleet. The validation tape-out.

**InnerJib7EA** is the first silicon product of PopSolutions Sails. SKU
**POPC_16A** — embedded entry single-board RISC-V accelerator with 16 GB DDR5,
targeting edge AI inference and on-device fine-tuning.

This is a deliberately small first silicon: monolithic die in Skywater 130nm
via Google Open MPW shuttle, low cost, low risk. The goal is to validate the
end-to-end design flow (RTL → simulation → synthesis → P&R → tape-out → driver
→ application) with the smallest possible blast radius. Lessons from
InnerJib7EA inform the chiplet-based ForeTopsail7EA and MainTopsail7EA that
follow.

## Status

Starting (2026-05). RTL integration in progress. See open issues.

## Quick spec (target — to be locked via ADR in this repo)

| Parameter | Target |
|---|---|
| Process | Skywater 130nm (Open MPW) |
| Compute | 1 Compute Unit, RVA23 + RVV 1.0 + `Xpop_matmul` |
| DRAM | 16 GB DDR5-4800 SO-DIMM (single channel) |
| Host | PCIe Gen4 x4 (via LitePCIe) |
| TDP | < 25 W |
| Form factor | Mini-ITX SBC + M.2 accelerator variant |
| Reference workload | GGML int4 inference of TinyLlama-1.1B |
| BOM target | R$ 800–1500 |

## How this repo relates to MAST

InnerJib7EA vendors [`popsolutions/MAST`](https://github.com/popsolutions/MAST)
as a git submodule under `mast/`. MAST holds the shared IP (RISC-V core,
compute unit, memory controller, AXI4 interconnect, verification harness).
This repo holds only product-specific integration: top-level Verilog,
configuration, PCB design, datasheets, product tests.

When InnerJib7EA tape-outs to silicon, the MAST submodule is frozen at the
specific MAST release used. That submodule pin is the reproducibility
contract.

## License

Same dual-license model as MAST. See
[`popsolutions/MAST/NOTICE.md`](https://github.com/popsolutions/MAST/blob/main/NOTICE.md):

- Hardware contributions: CERN-OHL-S v2 (commercial dual-license available)
- Software contributions: Apache 2.0
- Documentation: CC-BY-SA 4.0

## Contributing

See [`popsolutions/MAST/CONTRIBUTING.md`](https://github.com/popsolutions/MAST/blob/main/CONTRIBUTING.md).
DCO sign-off required on every commit (`git commit -s`).

## Roadmap

See open issues. Major milestones for InnerJib7EA:

1. Lock spec (this repo, ADR-001-spec)
2. Top-level Verilog integration with MAST submodule
3. Verilator simulation runs end-to-end (TinyLlama-1.1B inference)
4. RTL synthesis area/timing report
5. Skywater 130nm Open MPW shuttle submission
6. First silicon validation
7. Driver + GGML backend hand-off to Spanker7EA
