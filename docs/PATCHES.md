# llama.cpp patches

`./install.sh` checks out llama.cpp at commit `18b5f8b1862ebfe0f1c33d2355b81a54d2fec867` into `vendor/llama.cpp` and applies the 27 patches in `patches/` with `git am`. Each patch is one commit whose subject starts with `byteplan:`. New behavior is opt-in or has an environment variable to switch it off; `bin/chat` sets the variables it needs.

## 0001 Refusal projection hook for qwen4exp

Runtime abliteration: at the output of layers 4 to 44, the refusal direction is projected out of each of the 4 hyper-connection streams, `h -= s·(h·v)·v` with `v` normalized per layer. Ported from Cudecnik's qwen4exp control-vector hooks and cut down to applying a finished direction file. It is off unless `BYTEPLAN_REFUSAL_PROJ` points to the direction GGUF; without it the graph is unchanged, so outputs stay bit-identical.

| Variable | Default | Meaning |
|---|---|---|
| `BYTEPLAN_REFUSAL_PROJ` | empty = off | path to the direction GGUF |
| `BYTEPLAN_REFUSAL_SCALE` | `1.0` | scale `s`; `0` switches it off, negative amplifies |
| `BYTEPLAN_REFUSAL_LAYERS` | `4-44` | inclusive layer range, capped at `n_layer-1` |

When active, the log shows a `load_projection_env: refusal projection ...` line. Invalid input (missing file, wrong `controlvector.model_hint` or dimension) or combining it with `--control-vector` stops context creation with a message. Side effect: stock `--control-vector` (additive) now also works on qwen4exp.

## 0002 Per-op GPU timing for Metal

A measurement tool, not a speedup: with `GGML_METAL_OP_PROFILE=1` every op or fused group runs in its own command buffer and its GPU time goes to stderr as `opprof\t<graph>\t<ops>\t<name>\t<n>\t<µs>`. Ops then run one at a time on an idle GPU, so the numbers are good for ranking ops, not for tokens per second. Without the variable nothing changes.

## 0003 Metal moe_reduce fusion for top-9/10 experts

The existing Metal fusion `MOE_REDUCE` (MUL plus the expert ADD chain in one kernel) only matched up to top-8. This raises `GGML_METAL_MOE_REDUCE_MAX_EXPERTS` to 10 and `GGML_METAL_FUSION_MAX` to 24 and adds the patterns for 9 and 10 experts, with new `test-backend-ops -o MOE_REDUCE` cases (+3.8 % decode on ista-o1). `GGML_METAL_FUSION_DISABLE=1` switches off all fusions; with 0008 the fused kernel is bit-identical to the unfused ops.

## 0004 Metal fusion of the qwen4exp hc_post gate chain

Port of Vulkan #29520: the `hc_post` kernel computes `post = 2·sigmoid(inject/hc)` while loading `post`, with the same formula as the three separate kernels, so SCALE, SIGMOID and SCALE disappear (new fusion `HC_POST_GATE`). The existing `test-backend-ops -o DSV4_HC_POST` tests (gated=1) run through the fused path. Switch off with `GGML_METAL_FUSION_DISABLE=1` or `GGML_METAL_FUSION_SKIP` (see 0008).

## 0005 Metal fusion of SCALE into SILU/SIGMOID

`SCALE` followed by `SILU` or `SIGMOID` becomes one unary dispatch (the kernel applies `scale·x+bias` before the op); it hits `silu(down/hc)` in the HC mix 96 times per token. Test: `test-backend-ops -o SCALE_UNARY`. The gain is small (≈ +0.3 %); switch off like 0004.

## 0006 Metal encoding knobs GGML_METAL_N_CB / GGML_METAL_N_MAIN

`GGML_METAL_N_CB` sets the number of extra encoder threads (default 1, max 8) and `GGML_METAL_N_MAIN` the number of nodes in the first command buffer (default max(64, 10 %)). Without the variables nothing changes. `bin/chat` uses `GGML_METAL_N_CB=8` (+4.8 % decode), because most of the host gap per token is encoding time.

## 0007 Web UI conversation compaction

Compacts a chat like Claude Code does: `/compact [focus]`, a button in the context gauge popup, or automatically before sending above a threshold (settings "Auto-compact conversations", default on, 80 %). The model summarizes the history and the chat continues in a new conversation "… (compacted)"; the original stays unchanged. Turn off the setting to compact only by hand; model outputs are not affected.

## 0008 Metal fusions bit-identical to the unfused ops

qwen4exp amplifies last-digit rounding differences to KL ≈ 0.01 to 0.03, so a fusion that only rounds differently looks like a bug, and with `GGML_METAL_N_CB=8` results would depend on where command-buffer boundaries cut fusion groups. This patch makes `moe_reduce` (0003) round like MUL plus the ADD chain and stops `RMS_NORM+SCALE` from reassociating; the upstream topk-moe fusion still rounds a little differently; `GGML_METAL_FUSION_SKIP=ARGSORT` turns it off, and the fused `N_CB=8` graph then matches the unfused one bit for bit. `bin/chat` keeps it on like stock llama.cpp (about 1 % faster, same answers in every benchmark run). New bisect knobs: `GGML_METAL_FUSION_SKIP=tok1,tok2` skips patterns whose label contains a token, `GGML_METAL_FUSION_ONLY=<label>` keeps only that one.

## 0009 Spar expert pool

Keeps only S of the 512 experts per layer in RAM and streams the rest from `experts.bin` (built by `tools/compiler/spar_pack.py`); opt-in with `--spar-experts <experts.bin>` and `--spar-slots S` (`bin/chat --spar S`), without them the normal model runs. It adds `GGML_OP_SPAR` (Metal) and `llama_spar`: a slot pool with LFU and aging, `pread` with `F_NOCACHE`, multi-pass MoE when a ubatch needs more experts than slots, per-layer slots from the profile of `tools/experts/profile.py`, router-based prefetch below 85 % slots, and an abort instead of silent errors when a load times out. Only residency and IO change, so outputs stay bit-identical (checked at S=512 and in multi-pass runs); `BYTEPLAN_SPAR_NOPROFILE=1` ignores the profile, `BYTEPLAN_SPAR_PREFETCH=0/1` forces prefetch off or on.

## 0010 Model loading progress in the 503 response and the web UI

The server already tracked the loading stages (text model, expert pool, MTP draft, vision) but only reported them in router mode. Now the 503 "Loading model" error carries `error.progress` `{stage, stages, value, overall}`, and the web UI loading banner shows percent, a progress bar and the current stage (polling every 500 ms). No knob; model outputs are not affected.

## 0011 Keep the system+tools checkpoint, prewarm it from the web UI

The server no longer evicts the checkpoint at the first user message, where the shared part of every new chat (system prompt and tool definitions) ends. Once the server is ready, the web UI sends that shared start once (`max_tokens 1`), so a new chat processes its start in 0.14 s instead of 4.4 s with 1.7k tokens of tools. Outputs are unchanged; there is no knob.

## 0012 Vision encoder on demand on the GPU

With `BYTEPLAN_MMPROJ_LAZY_GPU=1` and `--no-mmproj-offload` the CPU vision context stays for tokenization and capabilities, and the first image loads a GPU copy (0.37 s) that encodes it: a 1495-token screenshot takes 5.8 s instead of 164 s. The GPU copy is freed by the next request after 10 minutes without images. Without the variable the CPU encoder works as before; `bin/chat` sets it.

## 0013 Accept system messages after the first one (Claude Code, Codex)

Qwen's chat template stops with "System message must be at the beginning". Claude Code sends a system message after the user turn and Codex sends developer messages, so both failed. At load the server now probes whether the template accepts a later system message (`supports_late_system_role`, shown with the other template caps). If not, a leading run of system messages is merged into one and later ones go in as user messages at their place, so the cached start of the conversation stays the same. Requests without such messages are unchanged, so normal chats stay bit-identical. No knob.

## 0014 Keep the start of new chats on the SSD

The state at the first user message (system prompt and tool definitions) of the main and the MTP context goes to `$BYTEPLAN_MODELS/prompt-cache` once, together with the checkpoint of 0011. After a restart, a new chat or agent session with the same start loads it in 0.1 s instead of reading it again (33 s for 13,600 tokens, measured). Entries count only for the same model files, build, batch and context sizes, KV types and Byteplan settings. `BYTEPLAN_PROMPT_DISK=<dir>` turns it on (`bin/chat` and `bin/run` do), `BYTEPLAN_PROMPT_DISK_GB` (default 8) caps the folder, least recently used first. The loaded state is the saved one bit for bit and the prompt continues at the same batch boundary, so answers stay the same (checked with and without drafts).

## 0015 n-gram drafts of 8 to 15 tokens by default

Changes the defaults of `--spec-type ngram-mod` from lookup 24 / drafts 48 to 64 tokens to lookup 16 / drafts 8 to 15. A check of 16 tokens or fewer stays on Metal's few-row matmul kernels; with more rows llama.cpp switches to the large-batch kernels and a check costs several times as much. Measured with MTP on the M3 Max (5 alternating pairs): code edits +9 %, agent refactors +15 %, new code +4 %, prose unchanged. A batch of 16 rounds like llama.cpp's own MTP checks of 4 tokens (KL divergence 0.0021 vs 0.0020 against one token at a time, same perplexity, [results](results/kl-batch-rounding.txt)), so the agent answer differs from llama.cpp in rounding only. The old values: `--spec-ngram-mod-n-match 24 --spec-ngram-mod-n-min 48 --spec-ngram-mod-n-max 64`.

## 0016 mul_mm_id starts only the non-empty token tiles

The MoE matmul of a prompt chunk started (tokens/32) × 512 experts threadgroups per row block, and with 1024 tokens almost all of them returned at once (an expert gets about 20 tokens). `map0` now also writes where each expert's 32-token tiles start in one compact list, the kernel starts one threadgroup per list entry (at most tokens·10/32 + 512) and finds its expert by binary search. Same tiles, same arithmetic: the perplexity matches to the last digit. Prompt reading +1.4 % on its own.

## 0017 Rollback snapshots only for the slots a ubatch can use

With speculative decoding every DeltaNet and PLE layer copied its conv state into `n_rs_seq + 1` rollback slots in every graph, each copy behind a `ggml_cont`. A ubatch of n tokens is rolled back by at most n − 1 of them (the SSM snapshots already stop there), so only `min(n_rs_seq + 1, n)` slots are written, straight from the strided view. The values are the same; a verify graph has about 150 fewer GPU steps. The shared DeltaNet code (qwen3next, qwen35) gets the same rule.

## 0018 Full threadgroups for small Metal ops, delta-net state read in place

A GPU profile of a draft check (4 tokens, about 2,950 steps) showed small kernels that ran one thread per threadgroup: `ssm_conv` started one threadgroup per channel (10,240 of them), unary ops below 32k elements and binary row-broadcast ops below 64k elements one per element. They now run 256 threads per threadgroup with the same arithmetic per element, so every result is bit-identical; `ssm_conv` in a draft check drops from 52 to 6 µs.

`ggml_gated_delta_net_ids` reads each sequence's initial state from its row of the whole state cache (ids from `build_rs`), as `ggml_ssm_scan` already does for Mamba. qwen4exp no longer gathers a 3 MB copy of the state per DeltaNet layer in every graph. CPU and Metal implement the ids, and the op without ids is unchanged.

Same answers in every benchmark (checksums equal), ABBA over 6 pairs each: agent work, new code and prose +6 to +7 %, code edits +4 %, prompt reading +2 %.

## 0019 Op profile with tensor names and shapes

`GGML_METAL_OP_PROFILE` lines (patch 0002) get five more columns: the first source tensor's name, type and size, the rows of the second source, and the output shape. That is enough to rank matrix products by GB/s and to find slow small ops by shape. Profiling only; the first six columns stay as before.

## 0020 Expert map on all GPU cores, MoE tiles in 8-token rows

Before every expert matmul, `map0` sorts the tokens to their experts. It ran as one threadgroup on one of the 40 GPU cores and scanned every token for every expert (0.3 ms per call, three calls per layer). It now counts each expert's rows per chunk of 32 tokens (`map0_cnt`) and writes them after the rows of the earlier chunks, one threadgroup per chunk: the same lists in the same order. `kernel_mul_mm_id` gives each simdgroup 8 token rows of the tile, so a simdgroup without rows of the expert skips its MMAs (an expert gets about 20 tokens of a 1024-token chunk). Each output element sees the same MMA sequence, so the answers are bit-identical. MoE time per prompt chunk −9 %, prompt reading +2.2 %.

## 0021 Sparse prefill attention on simdgroup MMA, narrow rows, 64-row tiles

QSA picks 2,051 cells per token, the same for all 24 heads of the token. llama.cpp ran that selection with the decode kernel, one threadgroup per token and head: 25 ms per QSA layer for a 1024-token chunk. `kernel_flash_attn_ext_sparse` runs the 12 heads of a KV group as the rows of one tile on simdgroup MMA and loads each K/V row once, straight from the cache into the matrices: 8.4 ms. This kernel rounds differently; the KL against one-token-at-a-time decoding stays the same (0.00213 against 0.00202 ± 0.00013, same top token 98.91 % against 98.90 %). `BYTEPLAN_FA_SPARSE_MMA_OFF=1` keeps the old path.

Unary ops, `get_rows` and `repeat` put several narrow rows into one threadgroup (QSA built its selection with ops on rows of 1 or 4 values, 1.2 ms each). Dense matmuls of 512+ tokens take 64 instead of 32 tokens per threadgroup, so each dequantized weight tile serves twice the tokens (q3_K −12 %, iq4_xs and q8_0 −3 %). Both are bit-identical.

## 0022 The MTP head reads only the end of a long prompt

The draft head attends through QSA too, so its drafts read the end of the prompt. It now skips its catch-up for prompt positions older than `BYTEPLAN_MTP_PROMPT_TAIL` tokens (0 reads everything; patch 0026 sets the default to 1024). The main model still reads every token and checks every draft, so the answer after a 7,000-token prompt stays the same. Prompt reading +7 %.

## 0023 Delta-net runs 4 state columns per simdgroup

The DeltaNet recurrence walks the tokens one after another. Each simdgroup carried one column of the state and waited on its own chain of reductions. Now it carries 4 columns side by side, sharing the k/q loads, so the chains overlap. Each column keeps the same math, so the answers are bit-identical. Kernel for a 1024-token chunk 2.95 → 1.74 ms; prompt reading +10.7 %, writing +6 to +13 %.

## 0024 Q2_0 dequantizes in half, copies index in 32 bits

`(q − 1)·d` with q in 0..3 is exact in half precision (d is a half), so the matmul tiles that hold half values dequantize Q2_0 in half math: same values, less work in the expert kernels. `kernel_cpy` computes destination indices in 32 bits when the tensor fits, instead of four emulated 64-bit divisions per element. Bit-identical; prompt reading +7.5 %, writing +5 to +11 %.

## 0025 64-token tiles only where they leave enough threadgroups

For a narrow matrix with long rows, 64 tokens per threadgroup left too few threadgroups for 40 GPU cores: the 320-row hyper-connection matrix (10,240 wide) took 1.0 instead of 0.7 ms. The 64-token tile now needs 512+ threadgroups. Bit-identical.

## 0026 q8_0 dequantizes in half, MTP prompt tail 1024

`q·d` (q an int8, d a half) is rounded once to half either way, so q8_0 tiles take half math as well: same values. The MTP head reads the last 1024 instead of 2048 prompt tokens: prompt reading +3 %, same answer.

## 0027 8-row matmul tiles for matrices of at most 8 rows

The 4-row hyper-connection inject matrix ran in a 64-row tile, 60 rows of it padding. `kernel_mul_mm_n8` takes 8 weight rows and 8 tokens per threadgroup with the same MMA sequence per element: 4 × 2048 × 10,240 in q8_0 0.43 → 0.31 ms. Bit-identical.

## Rebasing

The patches are a plain series, applied in file order (also listed in `patches/series`). To move to a new llama.cpp commit, apply them there with `git am` (or `git am -3`), resolve conflicts, then regenerate:

```sh
git -C vendor/llama.cpp format-patch --zero-commit -o ../../patches <new-base>..HEAD
```

Delete the old `.patch` files first, refresh `patches/series`, set `LLAMA_SHA` in `install.sh` to the new base and keep the `byteplan:` subject prefix. `install.sh` checks that `vendor/llama.cpp` has exactly the commits of `patches/series` on top of that base.
