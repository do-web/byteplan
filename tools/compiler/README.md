# tools/compiler

You normally do not run these tools by hand: `./install.sh` runs `rewrite.py --router q8_0` on the downloaded model and, with `--spar` (or on Macs with less than 64 GB), `spar_pack.py` on its output.

- `rewrite.py`, the -O1 profile `dense-q8`: a streaming GGUF rewriter for qwen4exp. It quantizes the hyper-connection (HC) matmuls to Q8_0. Router (`--router`) and lm_head (`--lm-head`) are separate lossy switches, off by default, each measured on its own (target: mean KL increase ≤ 0.01 per switch). Header, KV metadata and all other tensors are copied byte for byte; further shards (the n-gram table) are hard-linked next to the output. Stock llama.cpp loads the result. Other architectures are rejected.
- `spar_pack.py` splits a qwen4exp GGUF into a trunk without the routed experts plus an `experts.bin` for the expert pool (`bin/chat --spar`). The file layout is in its docstring.

Models live in `$BYTEPLAN_MODELS` (default `~/byteplan-models`), binaries in `build/bin`.

```sh
cd tools/compiler && uv sync     # Python 3.12, gguf-py editable from vendor/llama.cpp/gguf-py (fetched by ./install.sh)
```

## Usage

```sh
M="${BYTEPLAN_MODELS:-$HOME/byteplan-models}"
RW=(tools/compiler/.venv/bin/python tools/compiler/rewrite.py
  --in "$M/ista/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf"
  --out "$M/ista-o1")

"${RW[@]}" --dry-run               # plan only: tensors, old/new types, Δ bytes per token per switch
"${RW[@]}"                         # HC -> Q8_0
"${RW[@]}" --router q8_0           # also router -> Q8_0 (what ./install.sh does)

tools/compiler/.venv/bin/python tools/compiler/spar_pack.py \
  --in "$M/ista-o1/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-dense-q8_0-router-q8_0-00001-of-00002.gguf" \
  --out "$M/ista-o1-spar"
```

| Option | Default | |
|---|---|---|
| `--in` | required | GGUF or shard 1 (`*-00001-of-0000N.gguf`) |
| `--out` | required | output directory, same volume as the source (hard links) |
| `--dense` | `q8_0` | type for the HC matmuls |
| `--router` | `keep` | `keep` or `q8_0` for `ffn_gate_inp` |
| `--lm-head` | `keep` | `keep`, `q8_0` or `q6_K` for `output.weight`, only from F32/F16/BF16 |
| `--dry-run` | off | plan and savings only |

Output name: `<prefix>-dense-q8_0[-router-q8_0][-lm-<type>]-0000i-of-0000N.gguf`. Shard 1 is written as `.part` and verified against the source. Then shards 2+ are linked, and only after that is shard 1 made read-only and renamed. If any step fails, the tool removes the `.part` file and the links. It stops before writing when:

- a following shard is missing (with `--dry-run` only a warning, so you can plan while shard 2 is still downloading) or contains target tensors itself
- `--out` is on a different volume than the source (the hard links would only fail after writing)
- `--lm-head` is used on an lm_head that is already quantized: requantizing adds to the error, and for ISTA (Q5_K) `q6_K` and `q8_0` would also be larger
- less than 30 GiB would be left free after writing (`MIN_FREE`)

`spar_pack.py` follows the same rules (`.part` files, hard links, same volume, 30 GiB reserve) and checks trunk and `experts.bin` against the source by sha256.

## Target tensors

Names from `vendor/llama.cpp/src/llama-arch.cpp` (`LLM_ARCH_QWEN4EXP`), shapes from `src/models/qwen4exp.cpp`. All are `GGML_OP_MUL_MAT` weights that every token reads in full. They are only rewritten if stored as F32/F16/BF16:

| Tensor | Shape (ne0, ne1) | real model |
|---|---|---|
| `blk.N.hc_attn_down`, `blk.N.hc_ffn_down` | 4·n_embd × hc_lr | 10240 × 320 |
| `blk.N.hc_attn_up`, `blk.N.hc_ffn_up` | hc_lr × 4·n_embd | 320 × 10240 |
| `blk.N.hc_attn_inject`, `blk.N.hc_ffn_inject` | 4·n_embd × 4 | 10240 × 4 |
| `output_hc_down`, `output_hc_up` | as above | |
| `blk.N.nextn.hc_head_down/up` (MTP file only) | as above | |
| `blk.N.ffn_gate_inp` (router, only with `--router q8_0`) | n_embd × n_expert | 2560 × 512 |

Deliberately left alone: `hc_*_norm` (elementwise `GGML_OP_MUL`, F32), `ffn_gate_inp_shexp` (1-D) and the other BF16 tensors (indexer `q_proj`/`k_proj`, `ssm_alpha`/`ssm_beta`, `ple_value`). -O1 only targets HC and router. `--dry-run` shows how much BF16 remains and the savings split by HC, router and lm_head.

For ISTA Q2_0 that is 290 HC targets (48·6 + 2 output HC) and 48 routers, all BF16. From the dimensions: HC is 639.6 M weights, **−0.600 GB per token**; `--router q8_0` adds 62.9 M weights, −0.659 GB in total. The lm_head there is Q5_K, so `--lm-head` stops.

## Quantization

- **Q8_0** through `gguf.quants` (numpy). `test_rewrite.py` checks that the result is bit-identical to `ggml_quantize_chunk`.
- **Q6_K** and anything gguf-py cannot quantize go through ggml itself: `ggml_quantize_chunk` from `build/ggml/src/libggml-base.a`, linked with `cc` into `.build/libggml-quant.dylib` on first use (again when the `.a` is newer). `llama-quantize --tensor-type` is not an option: it never quantizes `ffn_gate_inp` and cannot rewrite single tensors without a new base type.
- The source is dequantized in row blocks (BF16, F16, F32, K-quants via gguf-py), at most 32 MB of float32 per step. Copies use `pread` in 32 MB blocks, not mmap. RSS therefore does not grow with the model, only with the blocks and with `GGUFReader` parsing the KV metadata. With the real vocabulary (248k tokens, 247k merges) each reader costs about 0.9 GB and 5 s, and a rewrite holds two (source and verification).

## Verification

After every write, with no switch to turn it off:

- header and KV section byte-identical to the source
- same tensors in the same order and shape, types as planned
- every unchanged tensor sha256-identical (source vs output)
- every changed tensor: relative RMSE of the dequantized values < 5 %; the maximum per type change is printed

```sh
cd tools/compiler && uv run python -m unittest test_rewrite     # Q8_0 gguf-py == ggml, Q6_K roundtrip, target patterns
```

The end-to-end script (not part of this repo) runs on micro-qwen4exp, a small model with random weights: one rewrite per switch on sources derived with llama-quantize (HC in BF16 as in ISTA), a byte comparison of all HC tensors with llama-quantize's own Q8_0, a two-shard split, a synthetic file with the real vocabulary and the abort cases above. Results (M3 Max, 2026-10-07):

- the outputs load in stock `llama-bench` (Metal); verify passes, rel. RMSE BF16/F32 → Q8_0 ≤ 0.39 %
- peak RSS 277 to 343 MB on micro, 1.73 GB with the real `tokenizer.json` (two readers)
- splits, a missing shard 2, a foreign volume, a router in shard 2, a wrong architecture and the cleanup after a failed `os.link` were checked on synthetic files without weights

How to read the KL numbers there: the random net is chaotic. Source vs itself gives KL 0, but any 8-bit perturbation of the HC weights lands at a mean KL of about 0.15, ggml's own quantizer included (0.145). So the number only shows that the rewrite perturbs no more than ggml does; it says nothing about quality. The router alone flips 87 % of the top-1 tokens on micro (8 experts, top-2), which is why it is a separate switch.

Projected for the real model (throughput measured on the M3 Max: Q8_0 via gguf-py 151 M weights/s, Q6_K via ggml 63 M/s): 0.70 G target weights take about 5 s. Copying and hashing 2 × ~37 GB adds minutes, depending on the disk. Peak RSS: the 1.73 GB of the two readers plus the blocks, about 2.2 GB.

## Limits

- Router quantization is its own risk: llama-quantize always skips `ffn_gate_inp`, and with 512 experts a Q8_0 perturbation can flip top-10 expert choices. Its share of the savings is small (59 of 659 MB per token). Hence a separate switch, default `keep`.
- Random weights: micro shows correctness (verify, byte comparison with llama-quantize) and that the output loads. Quality on the real model needs a KL measurement there.
- Little-endian GGUF and `qwen4exp` only, shards 2+ without target tensors, `--out` on the source's volume.

## Small MTP helper (Q4_K_M, 2.8 GB instead of 4.2 GB)

The helper only proposes tokens; the main model checks every one. A more heavily quantized helper therefore cannot change the output, at most the acceptance rate. Measured: 0.655 (Q4) vs 0.649 (Q8). `./install.sh` does this step too:

```sh
M="${BYTEPLAN_MODELS:-$HOME/byteplan-models}"
build/bin/llama-quantize --allow-requantize \
  "$M/mtp/Qwen3.8-Flash-Next-MTP-Q8_0.gguf" \
  "$M/mtp/Qwen3.8-Flash-Next-MTP-Q4_K_M.gguf" Q4_K_M
```
