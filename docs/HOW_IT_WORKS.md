# How Byteplan works

Byteplan is [llama.cpp](https://github.com/ggml-org/llama.cpp) plus 27 small patches, a setup script and a launcher tuned for one model: Qwen3.8-Flash-Next (180B parameters, 6B active per token, 512 experts per layer).

**Rule: no quality loss.** Byteplan changes no weights, prunes no experts and has no "think less" mode. Kernels, fusions and caches are checked bit for bit: with greedy decoding they write exactly the same text as llama.cpp. Draft settings (section 1) may change rounding, but never more than llama.cpp's own drafts do.

## 1. Guess ahead, check exactly (MTP + n-gram drafts)

The model writes one token at a time. Checking several guessed tokens at once costs about as much as writing one.

- **MTP**: a small helper head (shipped with the model) guesses the next 3 tokens. `install.sh` gives it a 2-bit copy of its vocabulary head, so each guess reads 199 instead of 497 MiB; the big model still checks every guess against its full vocabulary.
- **n-gram drafts**: when you edit code or a document, most of the answer already exists in the conversation. Byteplan copies the likely continuation from there.

The big model checks every guess and keeps only what it would have written anyway. Wrong guesses cost a little time, never quality. n-gram drafts are 8 to 15 tokens long, so a check covers at most 16 tokens and stays on the GPU kernels for small batches; longer drafts would switch to the kernels for big batches, which cost several times as much.

Checking 16 tokens in one go rounds a tiny bit differently than writing one token at a time, and now and then that picks a different word. llama.cpp does the same with its own MTP helper: 1 of the 4 benchmark answers changes when you switch it on. Measured on 8,188 tokens of code, agent logs and prose against one token at a time, a batch of 16 drifts as little as llama.cpp's batch of 4 (KL divergence 0.0021 vs 0.0020, same top token 98.9 % for both, same perplexity; [raw numbers](results/kl-batch-rounding.txt)). For scale: sushi measured 0.06 to 0.21 for 4- to 2-bit files of this model against the 16-bit original ([COMPARISON.md](COMPARISON.md#quality-against-the-original-16-bit-model)). This is why code edits run at ~165 tokens/s instead of ~77.

## 2. Instant agent chats (prompt cache)

Agent apps send the same long start (system prompt + tool list: 1,700 tokens in the benchmark, often more in real apps) with every new chat. Plain llama.cpp reads it again each time (~4 s). Byteplan keeps a snapshot of the model state after that start and protects it from being evicted. The web UI warms it up once after the page opens. A new agent chat starts writing after ~0.2 s. The same start is also written to the SSD once, so after a restart it loads in 0.1 s instead of being read again (33 s for a 13,600-token agent start).

## 3. Expert pool for smaller Macs (`--spar S`)

Each token uses only 10 of the 512 experts per layer. With `--spar S`, only `S` experts per layer stay in memory; the others are read from the SSD when needed.

- The pool keeps the experts used most often recently (LFU with aging) and preloads a measured per-layer profile (`data/`).
- The router of the next layer is run early as a hint, so missing experts are already loading while the current layer computes.
- A long prompt is read in several passes, one per group of experts that fits.

The math stays the same, only where the weights live changes, so the answers are identical to a run without `--spar`. The cost is speed: the SSD needs ~0.45 ms per missing expert.

| `--spar` | memory saved | chat speed (measured) |
|---|---:|---:|
| off (512) | 0 | 55 tokens/s prose |
| 410 | 6.6 GB | 47 |
| 358 | 10 GB | 42 |
| 256 | 16 GB | slower, not in the benchmark yet |

## 4. Fewer GPU commands, same rounding

Per token the GPU runs thousands of tiny steps. Byteplan merges some of them (fusions) and groups the command buffers (`GGML_METAL_N_CB=8`). The merged kernels were rewritten so they round exactly like the unmerged ones. This model amplifies a 1-bit rounding difference into a different answer, so "almost the same" is not good enough here.

## 5. Reading long prompts

Reading a prompt is plain arithmetic on the GPU: the matrix products run at 10.5 to 12 TFLOPS, close to what the M3 Max can do. What was slow sat around them, found with a per-step GPU profile (patch 0019):

- **The attention of the 12 QSA layers** ran with the decode kernel, one token and one head at a time. A new kernel runs the 12 heads that share a selection together on the matrix units: 3× faster. It rounds differently, with the same measured drift against one token at a time (KL divergence 0.00213 vs 0.00202).
- **The DeltaNet recurrence** walks the tokens in order; each GPU group now carries 4 columns of the state instead of 1, so the waits overlap (1.7× faster, same bits).
- **The expert map** that sorts tokens to experts ran on one of 40 GPU cores. Narrow matrices and ops on rows of 1 to 8 values started thousands of nearly empty thread groups.
- **The MTP helper** reads only the last 1024 prompt tokens: its attention looks at the end anyway.
- **Chunks of 2048 tokens** (`bin/chat` up to 64k context): every token gets the same arithmetic in any chunk of 32 or more, so this changes no answer and costs ~1 GB.

Together: 465 → about 650 tokens/s for a 7,000-token prompt, level with sushi on this Mac.

## 6. Small things that add up

- **-O1 compile** (`install.sh`): the hyper-connection and router weights go from 16 to 8 bit. They are read for every token, so this saves ~0.6 GB per token. This is the only step that changes numbers: KL divergence 0.004, same top-1 token 98.4 % vs the original file. The llama.cpp comparison in the README runs on the same compiled file.
- **Images on demand**: the vision encoder stays in normal memory and gets a GPU copy when the first image arrives (5.8 s instead of 164 s on the CPU), freed after 10 minutes without images.
- **Loading progress**: the web UI shows a percentage while the 37 GB load.
- **Memory guard** (`bin/run-guarded`): checks free memory before the start and stops the model if macOS starts swapping heavily, so your Mac stays usable.

## What did not help

- Letting macOS cache the expert file (page cache): the reads bypass it, a copy through it was only 2 % faster.
- Prefetching two layers ahead: worse than one.
- Prompt chunks of 2048 at 96k context: ran out of memory, so `bin/chat` uses 1024 there. 4096 tokens per chunk: no faster, and writing got 17 % slower.
- Running 4 heads per group in the old attention kernel: 2.2× slower (the kernel ran out of registers). Merging two hyper-connection matrices into one view: slower. Double buffers in the expert kernel: no gain.

Patch details: [PATCHES.md](PATCHES.md).
