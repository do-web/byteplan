# Byteplan, llama.cpp, sushi and Strata

All four run Qwen3.8-Flash-Next at home. Only Byteplan and llama.cpp were measured on the same Mac with the same test ([BENCHMARKS.md](BENCHMARKS.md)). The sushi and Strata numbers are their own published results on other hardware, so read them as a rough guide, not as a race.

| | **Byteplan** | **llama.cpp** | **[sushi](https://github.com/beamivalice/sushi)** | **[Strata](https://github.com/Niko1221/Strata)** |
|---|---|---|---|---|
| Runs on | Mac (Apple Silicon) | almost anything | Mac (Apple Silicon) | Windows/Linux PC with NVIDIA or AMD card (12 GB+) |
| Engine | llama.cpp + 27 patches | | own engine (Zig, MLX) | own engine, parts of llama.cpp/ggml |
| Model file | ISTA Q2_0, -O1 compiled | any GGUF | own 2 to 4 bit files | Q2_0 to IQ3_S |
| Memory for this model | 64 GB, 48 GB with `--spar` (untested) | 64 GB | 48 GB, 32 GB with streaming | 32 GB RAM + 12 GB VRAM |
| Quality of the unmodified engine | **yes**: kernels and caches bit for bit, except one prompt kernel with the same measured drift; longer drafts change rounding only, as much as llama.cpp's own MTP | (reference) | streaming and MTP yes; some defaults are lossy (attention quantization, 8-bit KV cache) | not checked |
| Guess-and-check drafts | MTP + copy from context | MTP (copy from context optional) | MTP (adaptive) + copy from context | MTP |
| Instant start for agent chats | yes (0.2 s) | no (4 to 5 s) | prefix cache in RAM and on SSD | not checked |
| Experts not in memory | read from SSD (`--spar`) | | read from SSD | computed by the CPU from RAM |

## Measured on the same Mac: Byteplan vs sushi

MacBook Pro M3 Max 64 GB, power adapter, 2026-10-11. Both at about 2 bit and the same size in memory (35 GB): Byteplan with the ISTA Q2_0 file, sushi v1.2.1 (`beamster/Qwen3.8-Flash-Next-Sushi-2bpw`, built from source). Same four tasks as [BENCHMARKS.md](BENCHMARKS.md), greedy, thinking off, 16k context, median of 2 rounds (order A B C, then C B A). Both engines measured the same way on the client: streaming, tokens between the first and the last token. Raw data: [results/2026-10-11-vs-sushi-m3-max-64gb.json](results/2026-10-11-vs-sushi-m3-max-64gb.json), script: `tools/bench/vs_sushi.py`. The prompt row comes from two extra tests with 4 rounds and 3 fresh prompts per engine start ([raw numbers](results/2026-10-11-prompt-vs-sushi.txt)).

| tokens/s | Byteplan | sushi (default) | sushi (lossless: `--kv-quant 16 --no-decode-attn-quant`) |
|---|---:|---:|---:|
| edit code | **143** | 99 | 99 |
| refactor (agent) | **98** | 95 | 93 |
| write new code | **77** | 75 | 74 |
| write prose | **55** | 54 | 52 |
| read a long prompt (7,000 tokens) | **647 to 658** | | 630 to 649 |
| new agent chat, seconds before writing | **0.21 s** | 2.73 s | 2.77 s |
| load the model | 12 s | 13 s | **9 s** |

- Byteplan reads long prompts a little faster than sushi: +1.4 % and +2.6 % in the two prompt tests. With one prompt per start (the main run) all three landed within 2 % of each other (587, 589, 598). A day earlier sushi was 30 % ahead; patches 0020 to 0027 and 2048-token prompt chunks closed the gap ([HOW_IT_WORKS.md](HOW_IT_WORKS.md#5-reading-long-prompts)).
- Byteplan writes new text 2 to 6 % faster and agent work 3 to 5 % faster. Three external displays were connected during these runs and the Mac ran hot, so both engines wrote about 10 to 20 % slower than in [BENCHMARKS.md](BENCHMARKS.md); the order A B C, C B A gives both the same conditions.
- Byteplan is faster when text repeats (code edits +44 %) and when an agent chat starts (13×), and keeps that start on the SSD across restarts.
- sushi's default settings changed the answers for new code and prose compared with its lossless settings, without being clearly faster. Byteplan keeps llama.cpp's quality: where its text differs, it is rounding of the same size as llama.cpp's own MTP ([BENCHMARKS.md](BENCHMARKS.md)).
- The two 2-bit files are built differently (ISTA GSQ-RCO vs EXL3). Which one is closer to the original model was not measured here.

## Published speed

| | Mac / PC | writes (tokens/s) | reads a prompt (tokens/s) | source |
|---|---|---:|---:|---|
| Byteplan | M3 Max 64 GB | 57 prose, 80 new code, 162 code edits | 454 | [BENCHMARKS.md](BENCHMARKS.md) |
| llama.cpp | M3 Max 64 GB | 51 prose, 74 new code, 76 code edits | 440 | same run |
| sushi | M5 Max 128 GB, 2.6 bit | 90 to 92 (code completion) | 1,900 to 2,200 | [benchmarks.md](https://github.com/beamivalice/sushi/blob/main/benchmarks.md) |
| sushi | M4 Max 64 GB, 3 bit (community) | 60 to 65 | ~690 | same |
| Strata | RTX 5070 12 GB, Q2_0 | 94 | 2,650 | [README](https://github.com/Niko1221/Strata#how-fast-is-it) |
| Strata | RX 9070 XT 16 GB, Q2_0 | 60 | 1,160 | same |

## Quality against the original 16-bit model

Smaller files lose some accuracy. Each project measures that differently, so the numbers below cannot be compared one to one.

| | file | weights in GPU memory | published quality | source |
|---|---|---:|---|---|
| Byteplan | ISTA GSQ-RCO Q2_0 (2.4 bit) | 35 GiB | 96 % of the original's task average (AIME25 96.7, GPQA-Diamond 89.4, LiveCodeBench v6 81.1 vs 100 / 91.9 / 87.4) | [ISTA-DASLab](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) |
| sushi | 2 / 2.6 / 3 / 4 bit | 35 / 44 / 50 / 64 GiB | KL divergence 0.208 / 0.136 / 0.104 / 0.059 | [qwen4-kld.md](https://github.com/beamivalice/sushi/blob/main/docs/qwen4-kld.md) |
| Strata | Q2_0 to IQ3_S | up to the card's VRAM, rest in RAM | see their model guide | [MODELS.md](https://github.com/Niko1221/Strata/blob/main/docs/MODELS.md) |

Byteplan's -O1 compile adds a small change on top of the ISTA file (KL divergence 0.004 against it). Everything else in Byteplan either keeps the answers bit-identical (kernels, fusions, caches, `--spar`) or changes rounding only, no more than llama.cpp's own MTP does (n-gram drafts, see [BENCHMARKS.md](BENCHMARKS.md); the prompt attention kernel of patch 0021 drifts as much as the kernel it replaces). The KL divergence of the ISTA file against the 16-bit model was not measured here: that needs the 354 GB original.

## Which one should I use?

- **Mac with 64 GB, you want llama.cpp's quality, faster code edits and instant agent chats:** Byteplan.
- **Mac with less memory, or a new M5 Mac:** try sushi. It reads long prompts much faster on M4/M5.
- **Windows or Linux PC with a gaming card:** Strata.

Strata was not run: it does not run on macOS.
