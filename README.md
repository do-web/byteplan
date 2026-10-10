<h1 align="center">Byteplan</h1>

**English** · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt-BR.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

<p align="center"><b>Run Qwen3.8-Flash-Next, a 180-billion-parameter AI model, on your Mac</b><br>
Same quality as llama.cpp, 2× faster when it edits code, agent chats start 18× sooner · free and open source</p>

Byteplan runs **[Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)** on a Mac with Apple Silicon. It chats, writes code, reads pictures and works with your apps and coding agents. Nothing leaves your Mac. It can also run [other models](#other-models) from Hugging Face with one command.

## How fast is it?

Measured on a MacBook Pro M3 Max with 64 GB, against plain [llama.cpp](https://github.com/ggml-org/llama.cpp) with the same model file and the same helper. A token is about ¾ of a word.

| | llama.cpp | **Byteplan** |
|---|---:|---:|
| Edits code (repeats much of your file) | 76 tokens/s | **162 tokens/s** |
| Refactors code in an agent | 69 tokens/s | **108 tokens/s** |
| Writes new code | 74 tokens/s | **80 tokens/s** |
| Writes text | 51 tokens/s | **57 tokens/s** |
| Reads a long prompt | 440 tokens/s | **454 tokens/s** |
| New agent chat: wait before the first word | 3.8 s | **0.2 s** |

Since 2026-10-11 Byteplan reads long prompts 26 % faster with the same answers, level with sushi ([details](docs/COMPARISON.md#measured-on-the-same-mac-byteplan-vs-sushi)). This table will be measured again.

**Same quality as llama.cpp:** same model file, no weight changed, no work skipped. Checking many guessed words at once rounds a tiny bit differently than writing one word at a time, so now and then a single word differs. llama.cpp does that too: its own helper changes 1 of the 4 test answers, and Byteplan's answers match llama.cpp's in 3 of 4. Measured over 8,000 tokens, both drift equally little ([details](docs/HOW_IT_WORKS.md#1-guess-ahead-check-exactly-mtp--n-gram-drafts)). Byteplan is faster where text repeats and when a chat starts; for brand-new text it is 8 to 12 % faster. All numbers, the method and how to measure it on your Mac: [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

<p align="center"><a href="https://buymeacoffee.com/doweb"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50"></a><br>
<sub>Byteplan is free. If it saves you time, a coffee helps me keep improving it.</sub></p>

## What you need

| | |
|---|---|
| **Mac** | Apple Silicon (M1 or newer). Tested: MacBook Pro M3 Max. Chips with less memory bandwidth (Pro, base M) are slower. |
| **Memory** | **64 GB** (tested). 48 GB should work with `--spar 256` (not tested yet). Less: only [smaller models](#other-models). |
| **Disk** | 150 GB free during setup, about 70 GB afterwards (+37 GB for `--spar`). |
| **Tools** | Xcode command line tools and [Homebrew](https://brew.sh). The installer tells you if something is missing. |

### How much text it keeps in mind (context)

| Context | about | Mac with 64 GB | Mac with 48 GB (untested) |
|---|---|---|---|
| 64k tokens (default) | 100 pages | `bin/chat` | `bin/chat --spar 256` |
| 96k tokens | 145 pages | `bin/chat --long` | `bin/chat --long --spar 256` |
| 256k tokens (the model's maximum) | 390 pages | `bin/chat --max --spar 358` | does not fit |

More context needs more memory (~1.4 GB per extra 32k tokens). When a chat gets longer than the context, the oldest part falls out; the web UI can summarize it for you (Compact).

## Install

### Let your AI set it up

Do you use an AI coding assistant (Claude Code, Cursor, Codex, ...)? Paste this into it:

```text
Set up Byteplan on this Mac for me: https://github.com/do-web/byteplan - follow docs/AI_SETUP.md in that repository.
```

### Or do it yourself

Open the Terminal app and paste these lines one by one:

```sh
xcode-select --install                 # once; skip if it says "already installed"
brew install git cmake node uv
git clone https://github.com/do-web/byteplan && cd byteplan
./install.sh                           # 64 GB Mac (48 GB: ./install.sh --spar)
```

The installer builds Byteplan (a few minutes), downloads the model (about 70 GB) and prepares it. If the download stops, run `./install.sh` again: it continues where it stopped.

## Using it

```sh
bin/chat
```

Wait until it says the model is loaded (the browser page shows a progress bar), then open **http://127.0.0.1:8080**. Stop it with `Ctrl-C`.

- **Your apps:** add an "OpenAI-compatible" provider with the base URL **`http://127.0.0.1:8080/v1`** (any API key, any model name). Coding agents: see below.
- **Let the model work on your files:** `bin/chat --agent` gives the chat tools to read and write files and run commands. Only on your own Mac.
- **Pictures:** attach them in the chat. The first picture takes a few seconds longer.
- **Not enough memory?** `bin/chat --spar 410` (or 358, 256) keeps fewer experts in memory. The answers stay exactly the same, only slower ([numbers](docs/HOW_IT_WORKS.md#3-expert-pool-for-smaller-macs---spar-s)). Needs `./install.sh --spar` once.
- **Fewer refusals:** `bin/chat --uncensored`, off by default ([what it does](docs/UNCENSORED.md)).

### Coding agents (Claude Code, Codex)

Agents send long instructions and tool lists, so give them more context: start `bin/chat --long` (96k) or `bin/chat --max --spar 358` (256k). The first answer takes 30 to 70 seconds while the model reads those instructions (Codex about 12,000 tokens, Claude Code about 26,000; more with many MCP servers). Byteplan keeps them on the SSD, so the next session starts within seconds, also after a restart (Claude Code with 51,000 tokens: about 90 s the first time, 25 s after a restart).

**Claude Code**, in a second terminal:

```sh
export ANTHROPIC_BASE_URL=http://127.0.0.1:8080 ANTHROPIC_AUTH_TOKEN=local
export ANTHROPIC_MODEL=qwen3.8-flash-next ANTHROPIC_DEFAULT_HAIKU_MODEL=qwen3.8-flash-next
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=90000    # a bit below bin/chat --long (98,304): Claude Code counts tokens differently
claude
```

If it says the request exceeds the context size, many MCP servers are making every request longer: use `bin/chat --max --spar 358` and `CLAUDE_CODE_MAX_CONTEXT_TOKENS=240000`, or start `claude --strict-mcp-config` without them.

**Codex**: add this to `~/.codex/config.toml`, then run `codex`:

```toml
model = "qwen3.8-flash-next"
model_provider = "byteplan"
model_context_window = 90000

[model_providers.byteplan]
name = "Byteplan"
base_url = "http://127.0.0.1:8080/v1"
wire_api = "responses"
```

## Other models

```sh
bin/run Qwen/Qwen3-8B-GGUF                         # a ready-made GGUF model
bin/run https://huggingface.co/Qwen/Qwen3-8B       # original weights: converted once
bin/run qwen3 8b                                   # not sure about the name? shows matches
```

`bin/run` downloads the model, picks the best size that fits your memory (8-bit if it fits: almost no quality loss), converts original weights to GGUF the first time, and starts the same web UI. Choose a size yourself with `:Q4_K_M` (faster) or `:Q8_0` (more accurate). Run `./install.sh --no-model` first if you only want other models.

Other models get the general speed-ups (guess-and-check drafts, faster agent starts, pictures on demand, memory guard). The expert pool and the -O1 compiler are made for Qwen3.8-Flash-Next only.

### Which model for my Mac?

| Memory | Model | Start with | Size | Good for |
|---|---|---|---:|---|
| 16 GB | Gemma 4 E4B | `bin/run unsloth/gemma-4-E4B-it-qat-GGUF` | 3.9 GB | everyday chat, pictures |
| 16 GB | Qwen3.5 4B | `bin/run unsloth/Qwen3.5-4B-GGUF` | 4.2 GB | small code tasks, tools |
| 24 GB | MiMo-V2.6 Distill 9B | `bin/run ggml-org/MiMo-V2.6-Distill-Qwen-9B-GGUF` | 8.9 GB | code and agents |
| 24 GB | Gemma 4 12B | `bin/run unsloth/gemma-4-12B-it-qat-GGUF` | 6.3 GB | chat, pictures |
| 32 GB | Qwen3.6 35B-A3B | `bin/run unsloth/Qwen3.6-35B-A3B-GGUF` | 16.8 GB | fast all-rounder (MoE) |
| 32 GB | Qwen3.8 27B | `bin/run unsloth/Qwen3.8-27B-GGUF` | 16.4 GB | strongest coder that fits, slower |
| 48 GB | Qwen3.8 27B | `bin/run unsloth/Qwen3.8-27B-GGUF` | 27.1 GB | the same, 8-bit |
| 64 GB | **Qwen3.8-Flash-Next** | `bin/chat` | 37 GB | **the main model: best quality** |
| 64 GB | Qwen3.6 35B-A3B | `bin/run ggml-org/Qwen3.6-35B-A3B-GGUF` | 34.4 GB | fast MoE, 8-bit, with MTP helper |
| 96–128 GB | Laguna S 2.1 118B-A8B | `bin/run unsloth/Laguna-S-2.1-GGUF` | 68–91 GB | agentic coding |

Sizes are what `bin/run` picks on that Mac. **MoE** models ("A3B" = 3 billion parameters active per word) are fast on a Mac; **dense** models read all their weights for every word, so they are slower but often smarter. All models above can keep the start of agent chats on the SSD; repos with an `mtp-` file also get the MTP helper.

**Not worth it:** dense 70B+ models (slow on a Mac and weaker than Qwen3.8 27B), 200B+ MoE models squeezed into 1 to 3 bit, a 2-bit 35B instead of an 8-bit 9B, and repos that are no chat models (names with `-Base`, Gemma without `-it`, OCR, speech or embedding models).

## Byteplan and other projects

| | Byteplan | [sushi](https://github.com/beamivalice/sushi) | [Strata](https://github.com/Niko1221/Strata) |
|---|---|---|---|
| Runs on | Mac | Mac | Windows/Linux PC with a gaming card |
| Quality of the unmodified engine | yes, only rounding differs (as with llama.cpp's own helper) | its defaults are lossy (quantized attention and KV cache) | not checked |
| Code edits / new text (tokens/s, same M3 Max, 2-bit) | **143** / 55 to 77 | 99 / 52 to 75 | (PC only) |
| Reads a prompt (tokens/s) | **647 to 658** | 630 to 649 | (PC only) |
| New agent chat starts after | **0.2 s** | 2.7 s | (PC only) |

On this Mac Byteplan reads long prompts 1 to 3 % faster than sushi and writes new text 2 to 6 % faster; it edits code 44 % faster, starts agent chats 13× sooner and keeps llama.cpp's quality. Details and sources: [docs/COMPARISON.md](docs/COMPARISON.md).

## How does it work?

- **Guess, then check:** a small helper guesses the next words, and Byteplan copies likely text from the conversation (code edits repeat a lot). The big model checks all guesses at once and keeps only what it would have written anyway.
- **Ready for agents:** the long start that agent apps send with every chat is kept in memory and on the SSD, so a new chat starts at once, also after a restart.
- **Fewer steps on the GPU:** small GPU steps are merged, rewritten so they round exactly like before.
- **Expert pool:** the model has 512 experts per layer and uses 10 per word. With `--spar`, only the most used stay in memory and the rest load from the SSD just in time.
- **Memory guard:** checks free memory before the start and stops the model before your Mac starts swapping.

More: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) · the llama.cpp changes: [docs/PATCHES.md](docs/PATCHES.md)

## Something went wrong?

- **"not enough free RAM"**: close other apps (browsers and Docker use a lot) or use `--spar 410`.
- **"stopped by the memory watchdog"**: same fix. The guard stopped the model before macOS slowed down.
- **"swap in use"**: macOS still holds swapped memory from earlier. Restart the Mac.
- **The page says "Loading model" for a while:** normal on the first start (37 GB to read). Later starts are faster.
- **`./install.sh` stopped:** run it again; it continues. The log is in `install.log`.

Still stuck? Open an [issue](https://github.com/do-web/byteplan/issues) with your Mac, memory and the last lines from the terminal.

## Credits and license

Byteplan stands on [llama.cpp](https://github.com/ggml-org/llama.cpp) (MIT), the [Qwen](https://huggingface.co/Qwen) team's model, the quantized files by [ISTA-DASLab](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF), the MTP helper by [Joakimpalm-Zen](https://huggingface.co/Joakimpalm-Zen/Qwen3.8-Flash-Next-MTP-GGUF) and the refusal direction by [Cudecnik](https://huggingface.co/Cudecnik/Qwen3.8-Flash-Next-refusal-projection). Byteplan is open source under the [MIT License](LICENSE). The model has its own license (Qwen Community License 1.0, see [NOTICE](NOTICE)). This repository contains no model weights.

## Support

Byteplan is free and open source. If it is useful to you, you can support its development:

<a href="https://buymeacoffee.com/doweb"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40"></a>
