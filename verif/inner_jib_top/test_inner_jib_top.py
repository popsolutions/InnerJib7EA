# SPDX-License-Identifier: Apache-2.0
"""End-to-end Sprint C test: a real RISC-V program (sum_ints) running
on the upstream core, fetching instructions through MAST's AXI4 chain,
producing the expected output sequence on the core's `out`/`outen` ports.

This is the validation milestone that proves the full integration:
  upstream core → core_axi4_adapter → axi4_master_simple → axi4_mem_model

If this test passes, every subsequent program (factorial, primes,
matrix multiply, eventually GGML kernels) lands on the same path.
"""
import os
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

CLK_PERIOD_NS = 10
PROG_BASE_ADDR = 128       # matches the assembler --offset 128 we used


def fixture_path():
    """Locate the pre-assembled sum_ints.hex shipped with this testbench."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "fixtures", "sum_ints.hex")


def load_hex_words(path):
    with open(path) as f:
        return [int(line.strip(), 16) for line in f if line.strip()]


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.ena.value = 0
    dut.set_pc_req.value = 0
    dut.set_pc_addr.value = 0
    dut.loader_en.value = 0
    dut.loader_addr.value = 0
    dut.loader_data.value = 0
    for _ in range(8):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)


async def load_program(dut, words, base_addr):
    """Push each 32-bit word into the mem_model via the back-door loader."""
    for i, word in enumerate(words):
        dut.loader_en.value = 1
        dut.loader_addr.value = base_addr + i * 4
        dut.loader_data.value = word
        await RisingEdge(dut.clk)
    dut.loader_en.value = 0
    await RisingEdge(dut.clk)


async def start_core_at(dut, pc):
    dut.set_pc_addr.value = pc
    dut.set_pc_req.value = 1
    await RisingEdge(dut.clk)
    dut.set_pc_req.value = 0
    dut.ena.value = 1
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_reset(dut):
    """After reset, halt is low, no output activity."""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())
    await reset_dut(dut)
    assert int(dut.halt.value) == 0
    assert int(dut.outen.value) == 0
    assert int(dut.outflen.value) == 0


@cocotb.test()
async def test_sum_ints_runs_and_halts(dut):
    """Run sum_ints.asm end-to-end; expect [0, 5, 4, 3, 2, 1, 0, 15] then halt.

    The expected output sequence comes from a hand-trace of sum_ints.asm:
      li x1, 5           # x1 = 5
      li x2, 0           # x2 = 0
      outr x2            # emit 0
      loop:
        outr x1          # emit 5, then 4, 3, 2, 1
        add x2, x1, x2   # x2 += x1
        addi x1, x1, -1
        bne x1, x0, loop # exit when x1 == 0
      outr x1            # emit final x1 (0)
      outr x2            # emit final x2 (0+5+4+3+2+1 = 15)
      halt
    """
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())
    await reset_dut(dut)

    words = load_hex_words(fixture_path())
    assert len(words) > 0, "fixture hex is empty"

    await load_program(dut, words, PROG_BASE_ADDR)
    await start_core_at(dut, PROG_BASE_ADDR)

    # Capture out values until halt, with a generous cycle bound
    captured_int = []
    captured_float = []
    halted = False
    for _ in range(50000):
        await RisingEdge(dut.clk)
        if int(dut.outen.value):
            captured_int.append(int(dut.out.value))
        if int(dut.outflen.value):
            captured_float.append(int(dut.out.value))
        if int(dut.halt.value):
            halted = True
            break

    assert halted, (
        f"core did not halt within 50000 cycles\n"
        f"  captured int outputs:   {captured_int}\n"
        f"  captured float outputs: {captured_float}"
    )

    expected = [0, 5, 4, 3, 2, 1, 0, 15]
    assert captured_int == expected, (
        f"out sequence mismatch:\n"
        f"  expected {expected}\n"
        f"  got      {captured_int}"
    )
    assert captured_float == [], f"unexpected float outputs: {captured_float}"
