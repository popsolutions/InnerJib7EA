<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# InnerJib7EA — POPC_16A

> First Sail of the PopSolutions fleet. The validation tape-out.

[![ci](https://github.com/popsolutions/InnerJib7EA/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/popsolutions/InnerJib7EA/actions/workflows/ci.yml)

**InnerJib7EA** is the first silicon product of PopSolutions Sails. SKU
**POPC_16A** — embedded entry single-board RISC-V accelerator with 16 GB DDR5,
targeting edge AI inference and on-device fine-tuning.

This is a deliberately small first silicon: monolithic die in Skywater 130nm
via Google Open MPW shuttle, low cost, low risk. The goal is to validate the
end-to-end design flow with the smallest possible blast radius.

## Status

**Sprint C (`inner_jib_top.sv` end-to-end integration) landed.** A real
RISC-V program (`mast/examples/direct/sum_ints.asm`) now runs through:

```
upstream core.sv -> core_axi4_adapter -> axi4_master_simple -> axi4_mem_model
```

The cocotb test pre-populates instruction memory through the mem model's
loader back-door (added in [MAST#8](https://github.com/popsolutions/MAST/pull/8)),
sets the core's PC, and asserts ena. The core then fetches instructions,
executes the loop, and emits the expected output sequence `[0, 5, 4, 3, 2,
1, 0, 15]` before halting.

This is the first program of any kind running on PopSolutions silicon-
equivalent hardware in simulation. Every subsequent program (factorial,
primes, matrix multiply, eventually GGML kernels) lands on the same path.

See [`docs/adr/0001-spec.md`](docs/adr/0001-spec.md) for the locked POPC_16A
specification.

## Quick spec

| Parameter | Target |
|---|---|
| Process | Skywater 130nm (Open MPW) |
| Compute | 1 Compute Unit, RVA23 + RVV 1.0 + `Xpop_matmul` |
| DRAM | 16 GB DDR5-4800 SO-DIMM (single channel) |
| Host | PCIe Gen4 x4 (via LitePCIe) |
| TDP | < 25 W |
| Form factor | M.2 22110 NGFF accelerator card |
| Reference workload | GGML int4 inference of TinyLlama-1.1B |
| BOM target | R$ 800–1500 |

## Run the testbench locally

One-time setup:

```bash
git clone --recursive git@git.pop.coop:pop/InnerJib7EA.git
cd InnerJib7EA
~/.pyenv/versions/3.12.10/bin/python3 -m venv mast/verif/.venv
source mast/verif/.venv/bin/activate
pip install cocotb cocotb-bus pytest
deactivate
ln -s ../mast/verif/.venv verif/.venv
```

Run:

```bash
source verif/.venv/bin/activate
cd verif/inner_jib_top
make
```

Expected output ends with:

```
** TESTS=2 PASS=2 FAIL=0 SKIP=0 **
```

## Relationship to MAST

InnerJib7EA vendors [`popsolutions/MAST`](https://github.com/popsolutions/MAST)
as a git submodule under `mast/`. MAST holds the shared IP (RISC-V core,
compute unit, AXI4 subsystem, verification harness). This repo holds only
product-specific integration: top-level Verilog (`src/inner_jib_top.sv`),
spec ADRs, eventually PCB design files, datasheets, product tests.

When InnerJib7EA tape-outs to silicon, the MAST submodule pin is frozen at
the specific MAST release used. That pin is the reproducibility contract.

## License

Same dual-license model as MAST. See
[`mast/NOTICE.md`](https://github.com/popsolutions/MAST/blob/main/NOTICE.md).

## Contributing

See [`mast/CONTRIBUTING.md`](https://github.com/popsolutions/MAST/blob/main/CONTRIBUTING.md)
and the cooperative-affiliate-only policy in
[`mast/GOVERNANCE.md`](https://github.com/popsolutions/MAST/blob/main/GOVERNANCE.md).
DCO sign-off required on every commit (`git commit -s`).
