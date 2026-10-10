# Benchmarks

## Result (MacBook Pro M3 Max, 64 GB, macOS 26.6, 2026-10-11)

Median of 2 rounds (order A B C D E, then E D C B A). Greedy decoding; the code after each number is a checksum of the answer, so equal codes mean equal text.

| Task (tokens/s) | llama.cpp | llama.cpp, no drafts | Byteplan | Byteplan `--spar 410` | Byteplan `--spar 358` |
|---|---:|---:|---:|---:|---:|
| edit code | 76 `#110ea42a` | 36 `#110ea42a` | **162** `#110ea42a` | 121 `#110ea42a` | 96 `#110ea42a` |
| refactor (agent) | 69 `#600f0858` | 36 `#600f0858` | **108** `#043884bf` | 92 `#043884bf` | 78 `#043884bf` |
| write new code | 74 `#3fd05bb5` | 36 `#3fd05bb5` | **80** `#3fd05bb5` | 67 `#3fd05bb5` | 58 `#3fd05bb5` |
| write prose | 51 `#15f62653` | 36 `#65946d7f` | **57** `#15f62653` | 50 `#15f62653` | 43 `#15f62653` |
| read a long prompt (6,951 tokens) | 440 | 463 | 454 | 385 | 359 |
| new agent chat, seconds before writing | 3.78 s | 3.59 s | **0.21 s** | 0.26 s | 0.31 s |
| memory for the model (64k context) | ~44 GB | – | ~44 GB | ~40 GB | ~36 GB |

Raw data: [results/2026-10-10-m3-max-64gb.json](results/2026-10-10-m3-max-64gb.json).

**What this shows**

- **Code edits 2× faster, agent refactors 1.5×**: copying likely text from the conversation (n-gram drafts of 8 to 15 tokens) on top of MTP.
- **New text 8 to 12 % faster**: same MTP helper, but with a 2-bit vocabulary head (each draft step reads 199 instead of 497 MiB), expert kernels that skip empty tiles (patch 0016), fewer state copies per step (patches 0017, 0018) and small GPU kernels that use full threadgroups (patch 0018).
- **Agent chats start 18× sooner**: the system prompt and tool list (1,673 tokens here) are cached and protected.
- **Same quality, rounding may differ.** llama.cpp's own MTP helper changes 1 of the 4 answers (prose) against the run without drafts. Byteplan matches llama.cpp in 3 of 4; the agent answer differs because Byteplan checks up to 16 guessed tokens at once. Both drift equally little from one-token-at-a-time decoding: KL divergence 0.0020 for a batch of 4 (llama.cpp's MTP check), 0.0021 for a batch of 16, same top token 98.9 % for both, same perplexity ([raw numbers](results/kl-batch-rounding.txt), 8,188 tokens of code, agent logs and prose). Kernels, fusions and caches alone change nothing: with the previous n-gram setting (48 to 64 tokens) all four answers were identical to llama.cpp.
- **`--spar` trades speed for memory**, same answers as without it: −6.6 GB costs 12 to 25 %, −10 GB 25 to 40 %. At `--spar 358` checks of 16 tokens need more experts from the SSD: code edits and agent work stay faster than llama.cpp, new text gets slower.

## Setup of the test

- **Same model file for both**: Qwen3.8-Flash-Next ISTA Q2_0 after the -O1 compile, MTP helper Q4_K_M, 16k context, one request at a time.
- **llama.cpp**: unmodified, same commit as Byteplan's base (`18b5f8b18`), `--spec-type draft-mtp --spec-draft-n-max 3`.
- **llama.cpp, no drafts**: the same build without the helper, one token per step. It is the reference for the checksums, not for speed.
- **Byteplan**: the build from `./install.sh`, `--spec-type draft-mtp,ngram-mod` (n-gram drafts 8 to 15 tokens, patch 0015), MTP helper with the 2-bit vocabulary head from `install.sh`, `GGML_METAL_N_CB=8`.
- **Prompt chunks**: 1024 tokens for all, as `bin/chat` used at the time. Patches 0020 to 0027 and chunks of 2048 (now the `bin/chat` default up to 64k context) came a day later: prompt reading +26 % with the same 1024 chunks and the same answers, more with 2048; against sushi see [COMPARISON.md](COMPARISON.md#measured-on-the-same-mac-byteplan-vs-sushi). This table gets measured again without external displays.
- **Tasks**: rename a function in an 84-line Python file and return the file; add docstrings to the same file (with the agent tool list); write a priority queue with tests; write 400 words about railway history. Up to 900 tokens each, `temperature 0`, thinking off.
- **Prompt reading**: 24,000 characters of this repository's own source code, nothing cached.
- **New agent chat**: tool list from `tools/bench/agent-tools.json`; Byteplan's web UI warms the cache once after the page loads, the test does the same.

Not measured here: quality on benchmarks like LiveCodeBench (the drift above is far smaller than the gap between two quantizations, so the scores would not move measurably), and the -O1 compile itself, which changes numbers slightly against the original ISTA file (KL divergence 0.004, top-1 agreement 98.4 %). Both columns use the compiled file.

## Run it yourself

Needs a finished `./install.sh`, about 46 GB of free memory, the power adapter and ~25 minutes. Close big apps first.

```sh
# unmodified llama.cpp at the same commit, for comparison
git clone https://github.com/ggml-org/llama.cpp /tmp/llama-stock && cd /tmp/llama-stock
git checkout 18b5f8b1862ebfe0f1c33d2355b81a54d2fec867
cmake -B build -DGGML_METAL=ON -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF && cmake --build build -j --target llama-server
cd -

tools/bench/proof.py --stock-bin /tmp/llama-stock/build/bin/llama-server --rounds 2 --out bench/proof.md
```

Without `ista-o1-spar` files (no `./install.sh --spar`), add `--only "llama.cpp (stock),Byteplan"`. Please share your results in an issue, especially from other Macs.
