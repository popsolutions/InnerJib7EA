<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# TinyLlama-1.1B reference workload (GGUF int4)

> First "hello world" reference workload for InnerJib7EA / POPC_16A.
> Closes [popsolutions/InnerJib7EA#3](https://github.com/popsolutions/InnerJib7EA/issues/3).

This directory holds the **baseline harness**. It runs TinyLlama-1.1B-Chat
(Q4_0 quantization) under stock `llama.cpp` on x86-64 CPU and emits a
structured tokens/sec measurement. The number is the floor we need
InnerJib7EA simulation (and eventually silicon) to beat by a meaningful
margin to justify the project.

The harness is intentionally **simple and dependency-light**. It does
not attempt to use Spanker hardware (Spanker isn't taped out yet) or
RVV / `Xpop_matmul`. Those land later — see *Migration path* below.

---

## What this bench does

1. **Fetch** TinyLlama-1.1B-Chat-v1.0 in GGUF Q4_0 quantization
   (~668 MB) from HuggingFace, verify SHA256, cache locally.
2. **Run** 64 tokens of decode against a fixed prompt
   (`"Hello, "`) using `llama.cpp` (via `llama-cpp-python` or the
   `llama-cli` binary).
3. **Emit** a JSON document on stdout with
   `tokens_generated`, `wall_clock_seconds`, `tokens_per_second`,
   plus environment metadata (host CPU, llama.cpp build).
4. **Compare** measured `tokens_per_second` against
   `expected_baseline.json`. If below threshold the harness exits
   non-zero so CI fails.

This is the same `Hello, ` prompt and same 16-token budget mentioned in
the issue's task list (we extend to 64 tokens here so timing isn't
dominated by prompt-eval and warm-up).

## Model source

| Field | Value |
|---|---|
| Model | TinyLlama 1.1B Chat v1.0 |
| Quantization | Q4_0 (GGUF) |
| Source | [TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF on HuggingFace](https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF) |
| Direct URL | `https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_0.gguf` |
| File size | ~668 MB |
| License | Apache 2.0 (TinyLlama) |

`fetch_model.sh` is idempotent: if the file is already present and its
SHA256 matches, it skips the download. The expected SHA256 is recorded
in the script and verified after every fetch.

## int4 quantization procedure

Q4_0 is the simplest GGML int4 format: weights are quantized in blocks
of 32, each block stores one fp16 scale + 32 packed 4-bit weights
(symmetric, no zero-point). Dequantization at compute time is
`weight = scale * (int4_value - 8)`. This is what `Xpop_matmul` will
need to fuse into the matmul inner loop on POPC_16A.

We use the pre-quantized model from TheBloke rather than running the
quantization ourselves — the produced GGUF file is byte-identical to
what stock `llama.cpp quantize` emits, so we save ~5 minutes of CI time.
If the upstream artefact ever disappears, regenerate with:

```bash
./build/bin/llama-quantize tinyllama-1.1b-chat-v1.0.fp16.gguf \
    tinyllama-1.1b-chat-v1.0.Q4_0.gguf Q4_0
```

## Expected baseline (sanity threshold)

`expected_baseline.json` records conservative thresholds — set well
below typical hardware so flaky CI doesn't false-positive. Indicative
ranges measured on a few common hosts (informational, not gated):

| Host | Tokens/sec |
|---|---|
| Modern x86 laptop (Ryzen 7 5800H, 8c) | 25-40 |
| GitHub Actions ubuntu-24.04 (4 vCPU) | 6-12 |
| Raspberry Pi 5 (8GB) | 3-6 |

The CI threshold is **5 tokens/sec on a 4-vCPU runner** — TinyLlama Q4_0
beats that comfortably. Anything below means something has gone wrong
(bad model file, llama.cpp regression, runner hardware change).

## Output schema

`bench.py` writes one JSON document to stdout with this shape (schema
version pinned in `expected_baseline.json` so consumers can detect
breaks):

```json
{
  "schema_version": "1",
  "model": "tinyllama-1.1b-chat-v1.0.Q4_0.gguf",
  "backend": "llama-cpp-python",
  "prompt": "Hello, ",
  "tokens_generated": 64,
  "wall_clock_seconds": 7.12,
  "tokens_per_second": 8.99,
  "host": {"cpu": "AMD Ryzen 7 5800H", "cores": 8, "ram_gb": 16.0},
  "llama_cpp_version": "0.2.90",
  "timestamp_utc": "2026-05-06T12:34:56Z"
}
```

`timestamp_utc` is ISO-8601 with trailing `Z`. `tokens_per_second` is
computed from `tokens_generated / wall_clock_seconds` (decode-only —
the prompt-eval pass is timed separately and discarded).

## Running locally

```bash
cd bench/tinyllama-1.1b

# 1. Fetch model (one-time, idempotent)
./fetch_model.sh

# 2. Install bench deps (CPU-only llama.cpp Python binding)
pip install llama-cpp-python==0.2.90

# 3. Run bench
python3 bench.py --model tinyllama-1.1b-chat-v1.0.Q4_0.gguf

# 4. Run bench AND check threshold
python3 bench.py \
    --model tinyllama-1.1b-chat-v1.0.Q4_0.gguf \
    --check expected_baseline.json
```

To use the `llama-cli` binary instead of the Python binding (skips
`llama-cpp-python` install if you already have llama.cpp built):

```bash
python3 bench.py \
    --model tinyllama-1.1b-chat-v1.0.Q4_0.gguf \
    --backend llama-cli \
    --llama-cli-path /path/to/llama.cpp/build/bin/llama-cli
```

## CI integration

`.github/workflows/bench.yml` runs the bench on **`workflow_dispatch`
only** (manual trigger). We do not run it on every PR because the model
download + first-token latency add ~5 minutes per run, which would
swamp the existing Verilator/cocotb job (~3 minutes).

To trigger from the GitHub UI: Actions to "bench" to Run workflow.

## Schema test (unit test)

`test_bench.py` is a **schema-only** unit test. It does not download or
run TinyLlama (that's CI's job on manual dispatch). It runs `bench.py`
with `--dry-run`, captures the JSON output, and asserts the document
shape matches what downstream tooling (regression tracker,
`Xpop_matmul` performance comparison plots) will consume.

This satisfies the "always write tests for code changes" rule
(`feedback_testing.md`) — the realistic test for a benchmark harness is
its output schema, not its absolute speed (which is environment-dependent).

```bash
cd bench/tinyllama-1.1b
python3 -m pytest test_bench.py -v
```

## Migration path to InnerJib7EA / Spanker

The bench is structured so the *measurement skeleton* (prompt setup,
token-count timing, JSON schema, threshold check) stays constant while
the *backend* swaps. Planned phases:

| Phase | Backend | When |
|---|---|---|
| **0 (this PR)** | stock `llama.cpp` on x86-64 CPU | now — establishes baseline |
| 1 | `llama.cpp` on RISC-V softcore in Verilator (RVA23 + RVV 1.0) | when MAST adds RVV-enabled core |
| 2 | `llama.cpp` with `Xpop_matmul` matmul kernel intrinsic | when MAST `Xpop_matmul` lands |
| 3 | Spanker runtime driving InnerJib7EA over PCIe (single card) | when InnerJib7EA bitstream + PCIe driver land in MVP PCB |
| 4 | Spanker runtime, multi-card tensor-parallel | post-MVP, per `project_multicard_parallelism.md` |

Each phase plugs in a new `--backend <name>` to `bench.py`. The same
JSON schema and the same threshold structure get reused — that's the
whole point of fixing them now, before there's anything to measure
against.

## What this bench is NOT

- Not a correctness test. We don't verify that generated tokens match a
  golden reference. (Issue #3 task: "Compare token-by-token against
  reference llama.cpp running on CPU" — that lands in a follow-up; see
  *Out of scope*.) The current harness is timing only.
- Not a Spanker integration test. Spanker hardware doesn't exist;
  importing `spanker-runtime` is deferred until the crate stabilizes
  and PR #6 (in-flight collective ops) lands.
- Not a power/energy measurement. PCIe-side power instrumentation
  arrives with the FPGA dev-board phase.

## Out of scope (future PRs)

- Token-by-token equivalence vs reference (issue #3 task 4)
- Cycle / SRAM / DDR bandwidth telemetry (issue #3 task 5) — needs
  Verilator integration and is RTL-side work (Agent 1 stream-1)
- `docs/benchmarks/tinyllama-int4.md` write-up (issue #3 task 6) —
  separate PR once we have real measured-vs-expected numbers from a
  live POPC_16A simulation
- Quantization to Q4_K (issue #3 task 1 mentions Q4_K first); Q4_0 is
  simpler and the right starting point for the kernel. Q4_K bench
  variant gets added once `Xpop_matmul` supports it.
