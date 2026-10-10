<h1 align="center">Byteplan</h1>

[English](README.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt-BR.md) · **简体中文** · [日本語](README.ja.md)

<p align="center"><b>在你的 Mac 上运行 Qwen3.8-Flash-Next，一个拥有 1800 亿（180B）参数的 AI 模型</b><br>
质量与 llama.cpp 相同，改代码时快 2×，智能体对话启动快 18× · 免费开源</p>

Byteplan 在搭载 Apple 芯片（Apple Silicon）的 Mac 上运行 **[Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)**。它能聊天、写代码、看图片，还能配合你的应用和编程智能体一起工作。所有数据都不会离开你的 Mac。它还能用一条命令运行 Hugging Face 上的[其他模型](#其他模型)。

## 有多快？

在一台 64 GB 的 MacBook Pro M3 Max 上测得，对比的是原版 [llama.cpp](https://github.com/ggml-org/llama.cpp)，使用相同的模型文件和相同的辅助模型。一个 token 大约相当于 ¾ 个英文单词。

| | llama.cpp | **Byteplan** |
|---|---:|---:|
| 修改代码（大量重复你文件里的内容） | 76 tokens/s | **162 tokens/s** |
| 在智能体里重构代码 | 69 tokens/s | **108 tokens/s** |
| 写新代码 | 74 tokens/s | **80 tokens/s** |
| 写文字 | 51 tokens/s | **57 tokens/s** |
| 读取很长的提示词 | 440 tokens/s | **454 tokens/s** |
| 新的智能体对话：等多久出现第一个字 | 3.8 s | **0.2 s** |

从 2026 年 10 月 11 日起，Byteplan 读取长提示词快了 26%，答案不变，与 sushi 持平（[详情](docs/COMPARISON.md#measured-on-the-same-mac-byteplan-vs-sushi)）。这张表会重新测量。

**质量与 llama.cpp 相同**：同一个模型文件，没有改动任何权重，也没有跳过任何计算。一次核对多个猜测的词时，舍入会和逐词书写略有不同，所以偶尔会有个别词不一样。llama.cpp 也是这样：它自带的助手会改变 4 个测试回答中的 1 个，而 Byteplan 的回答在 4 个中有 3 个与 llama.cpp 相同。在 8,000 个 token 上测量，两者的偏差同样小（[详情](docs/HOW_IT_WORKS.md#1-guess-ahead-check-exactly-mtp--n-gram-drafts)）。在文字重复和对话刚开始的时候，Byteplan 更快；写全新的文字时，它快 8% 到 12%。全部数据、测试方法，以及如何在你自己的 Mac 上测量：[docs/BENCHMARKS.md](docs/BENCHMARKS.md)。

<p align="center"><a href="https://buymeacoffee.com/doweb"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50"></a><br>
<sub>Byteplan 是免费的。如果它帮你省了时间，请我喝杯咖啡，能帮我继续改进它。</sub></p>

## 你需要什么

| | |
|---|---|
| **Mac** | Apple 芯片（M1 或更新）。已测试：MacBook Pro M3 Max。内存带宽较低的芯片（Pro、基础款 M）会更慢。 |
| **内存** | **64 GB**（已测试）。48 GB 配合 `--spar 256` 应该可以（尚未测试）。更少的话：只能用[较小的模型](#其他模型)。 |
| **硬盘** | 安装时需要 150 GB 空闲空间，之后约占 70 GB（使用 `--spar` 再加 37 GB）。 |
| **工具** | Xcode 命令行工具和 [Homebrew](https://brew.sh)。缺了什么，安装程序会告诉你。 |

### 它能记住多少文字（上下文）

| 上下文 | 大约 | 64 GB 的 Mac | 48 GB 的 Mac（未测试） |
|---|---|---|---|
| 64k tokens（默认） | 100 页 | `bin/chat` | `bin/chat --spar 256` |
| 96k tokens | 145 页 | `bin/chat --long` | `bin/chat --long --spar 256` |
| 256k tokens（模型的上限） | 390 页 | `bin/chat --max --spar 358` | 放不下 |

上下文越多，需要的内存越多（每多 32k tokens 需要 ~1.4 GB）。对话超过上下文长度时，最早的部分会被丢掉；网页界面可以帮你把它总结一下（Compact）。

## 安装

### 让你的 AI 帮你装

你在用 AI 编程助手吗（Claude Code、Cursor、Codex 等）？把下面这段话粘贴进去：

```text
Set up Byteplan on this Mac for me: https://github.com/do-web/byteplan - follow docs/AI_SETUP.md in that repository.
```

### 或者自己动手

打开“终端”应用，把下面几行一行一行地粘贴进去：

```sh
xcode-select --install                 # 只需一次；如果提示 "already installed" 就跳过
brew install git cmake node uv
git clone https://github.com/do-web/byteplan && cd byteplan
./install.sh                           # 64 GB 的 Mac（48 GB：./install.sh --spar）
```

安装程序会编译 Byteplan（几分钟），下载模型（约 70 GB）并做好准备。如果下载中断了，再运行一次 `./install.sh`：它会从中断的地方继续。

## 怎么用

```sh
bin/chat
```

等到它提示模型已加载（浏览器页面会显示进度条），然后打开 **http://127.0.0.1:8080**。用 `Ctrl-C` 停止。

- **你的应用**：添加一个“OpenAI 兼容”（OpenAI-compatible）的服务商，基础 URL 填 **`http://127.0.0.1:8080/v1`**（API key 和模型名称随便填）。编程智能体：见下文。
- **让模型处理你的文件**：`bin/chat --agent` 让聊天可以读写文件、运行命令。只在你自己的 Mac 上这样用。
- **图片**：直接在聊天里附上。第一张图片会多花几秒钟。
- **内存不够？** `bin/chat --spar 410`（或 358、256）会让内存里只保留较少的专家。回答仍然完全一样，只是会慢一些（[数据](docs/HOW_IT_WORKS.md#3-expert-pool-for-smaller-macs---spar-s)）。需要先运行一次 `./install.sh --spar`。
- **更少拒答**：`bin/chat --uncensored`，默认关闭（[它做了什么](docs/UNCENSORED.md)）。

### 编程智能体（Claude Code、Codex）

智能体会发送很长的说明和工具列表，所以要给它们更多上下文：用 `bin/chat --long`（96k）或 `bin/chat --max --spar 358`（256k）启动。第一个回答需要 30 到 70 秒，因为模型要先读完这些说明（Codex 大约 12,000 个 token，Claude Code 大约 26,000 个；MCP 服务器多时还会更多）。Byteplan 会把这些说明保存在 SSD 上，所以下一次会话几秒钟内就能开始，重启后也一样（Claude Code 带 51,000 个 token：第一次约 90 秒，重启后 25 秒）。

**Claude Code**，在第二个终端窗口里：

```sh
export ANTHROPIC_BASE_URL=http://127.0.0.1:8080 ANTHROPIC_AUTH_TOKEN=local
export ANTHROPIC_MODEL=qwen3.8-flash-next ANTHROPIC_DEFAULT_HAIKU_MODEL=qwen3.8-flash-next
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=90000    # 比 bin/chat --long（98,304）略小：Claude Code 计算 token 的方式不同
claude
```

如果它提示请求超出了上下文大小，说明很多 MCP 服务器让每次请求都变长了：改用 `bin/chat --max --spar 358` 和 `CLAUDE_CODE_MAX_CONTEXT_TOKENS=240000`，或者用 `claude --strict-mcp-config` 启动，不加载这些服务器。

**Codex**：把下面的内容添加到 `~/.codex/config.toml`，然后运行 `codex`：

```toml
model = "qwen3.8-flash-next"
model_provider = "byteplan"
model_context_window = 90000

[model_providers.byteplan]
name = "Byteplan"
base_url = "http://127.0.0.1:8080/v1"
wire_api = "responses"
```

## 其他模型

```sh
bin/run Qwen/Qwen3-8B-GGUF                         # 现成的 GGUF 模型
bin/run https://huggingface.co/Qwen/Qwen3-8B       # 原始权重：只转换一次
bin/run qwen3 8b                                   # 不确定名字？会列出匹配的模型
```

`bin/run` 会下载模型，挑选适合你内存的最佳大小（放得下就用 8-bit：几乎没有质量损失），第一次运行时把原始权重转换成 GGUF，然后启动同样的网页界面。想自己选大小，可以加 `:Q4_K_M`（更快）或 `:Q8_0`（更准确）。如果你只想用其他模型，先运行 `./install.sh --no-model`。

其他模型也能用上通用的加速功能（先猜后核对的草稿、更快的智能体启动、按需加载的看图功能、内存保护）。专家池和 -O1 编译器只为 Qwen3.8-Flash-Next 而做。

### 我的 Mac 该用哪个模型？

| 内存 | 模型 | 启动命令 | 大小 | 适合 |
|---|---|---|---:|---|
| 16 GB | Gemma 4 E4B | `bin/run unsloth/gemma-4-E4B-it-qat-GGUF` | 3.9 GB | 日常聊天、看图片 |
| 16 GB | Qwen3.5 4B | `bin/run unsloth/Qwen3.5-4B-GGUF` | 4.2 GB | 小型编程任务、工具调用 |
| 24 GB | MiMo-V2.6 Distill 9B | `bin/run ggml-org/MiMo-V2.6-Distill-Qwen-9B-GGUF` | 8.9 GB | 编程和智能体 |
| 24 GB | Gemma 4 12B | `bin/run unsloth/gemma-4-12B-it-qat-GGUF` | 6.3 GB | 聊天、看图片 |
| 32 GB | Qwen3.6 35B-A3B | `bin/run unsloth/Qwen3.6-35B-A3B-GGUF` | 16.8 GB | 快速的全能型（MoE） |
| 32 GB | Qwen3.8 27B | `bin/run unsloth/Qwen3.8-27B-GGUF` | 16.4 GB | 放得下的最强编程模型，较慢 |
| 48 GB | Qwen3.8 27B | `bin/run unsloth/Qwen3.8-27B-GGUF` | 27.1 GB | 同上，8-bit |
| 64 GB | **Qwen3.8-Flash-Next** | `bin/chat` | 37 GB | **主力模型：质量最好** |
| 64 GB | Qwen3.6 35B-A3B | `bin/run ggml-org/Qwen3.6-35B-A3B-GGUF` | 34.4 GB | 快速 MoE，8-bit，带 MTP 辅助模型 |
| 96–128 GB | Laguna S 2.1 118B-A8B | `bin/run unsloth/Laguna-S-2.1-GGUF` | 68–91 GB | 智能体编程 |

大小指的是 `bin/run` 在对应内存的 Mac 上挑选的版本。**MoE** 模型（“A3B” = 每个词激活 30 亿个参数）在 Mac 上很快；**稠密**（dense）模型每个词都要读取全部权重，所以更慢，但往往更聪明。上面所有模型都能把智能体对话的开头保存在 SSD 上；带有 `mtp-` 文件的仓库还能用上 MTP 辅助模型。

**不值得用**：70B 以上的稠密模型（在 Mac 上很慢，而且不如 Qwen3.8 27B）、硬压到 1 到 3 bit 的 200B 以上 MoE 模型、用 2-bit 的 35B 代替 8-bit 的 9B，以及不是聊天模型的仓库（名字带 `-Base` 的、不带 `-it` 的 Gemma、OCR、语音或嵌入模型）。

## Byteplan 和其他项目

| | Byteplan | [sushi](https://github.com/beamivalice/sushi) | [Strata](https://github.com/Niko1221/Strata) |
|---|---|---|---|
| 运行在 | Mac | Mac | 带游戏显卡的 Windows/Linux 电脑 |
| 质量与未修改的引擎相同 | 是，只有舍入不同（和 llama.cpp 自带助手一样） | 默认设置有损（注意力和 KV 缓存被量化） | 未核对 |
| 修改代码 / 写新文字（tokens/s，同一台 M3 Max，2-bit） | **143** / 55 到 77 | 99 / 52 到 75 | （仅限 PC） |
| 读取提示词（tokens/s） | **647 到 658** | 630 到 649 | （仅限 PC） |
| 新的智能体对话多久后开始 | **0.2 s** | 2.7 s | （仅限 PC） |

在这台 Mac 上，Byteplan 读取长提示词比 sushi 快 1% 到 3%，写新文字快 2% 到 6%；修改代码快 44%，智能体对话启动早 13×，并保持 llama.cpp 的质量。详情和来源：[docs/COMPARISON.md](docs/COMPARISON.md)。

## 它是怎么工作的？

- **先猜，再核对**：一个小的辅助模型猜接下来的词，Byteplan 还会从对话里复制很可能出现的文字（改代码时重复很多）。大模型一次核对所有猜测，只保留它本来就会写出的内容。
- **为智能体做好准备**：智能体应用每次对话都会发送一段很长的开头，这段内容会留在内存里和 SSD 上，所以新对话能马上开始，重启后也一样。
- **GPU 上的步骤更少**：把很小的 GPU 步骤合并起来，并改写成和以前完全一样的舍入方式。
- **专家池**：模型每层有 512 个专家，每个词用其中 10 个。使用 `--spar` 时，只有最常用的专家留在内存里，其余的在需要时及时从 SSD 加载。
- **内存保护**：启动前检查空闲内存，并在你的 Mac 开始使用交换内存（swap）之前停止模型。

更多内容：[docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) · 对 llama.cpp 的修改：[docs/PATCHES.md](docs/PATCHES.md)

## 遇到问题了？

- **"not enough free RAM"**：关掉其他应用（浏览器和 Docker 很占内存），或者使用 `--spar 410`。
- **"stopped by the memory watchdog"**：解决办法同上。内存保护在 macOS 变慢之前停止了模型。
- **"swap in use"**：macOS 还占着之前换出的内存。重启 Mac 即可。
- **页面一直显示 "Loading model"**：第一次启动时这很正常（要读取 37 GB）。之后启动会更快。
- **`./install.sh` 中断了**：再运行一次，它会继续。日志在 `install.log` 里。

还是没解决？请提交一个 [issue](https://github.com/do-web/byteplan/issues)，写上你的 Mac 型号、内存大小和终端里最后几行输出。

## 致谢和许可证

Byteplan 建立在这些成果之上：[llama.cpp](https://github.com/ggml-org/llama.cpp)（MIT）、[Qwen](https://huggingface.co/Qwen) 团队的模型、[ISTA-DASLab](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) 提供的量化文件、[Joakimpalm-Zen](https://huggingface.co/Joakimpalm-Zen/Qwen3.8-Flash-Next-MTP-GGUF) 提供的 MTP 辅助模型，以及 [Cudecnik](https://huggingface.co/Cudecnik/Qwen3.8-Flash-Next-refusal-projection) 提供的拒答方向（refusal direction）。Byteplan 以 [MIT 许可证](LICENSE)开源。模型有自己的许可证（Qwen Community License 1.0，见 [NOTICE](NOTICE)）。本仓库不包含任何模型权重。

## 支持

Byteplan 免费且开源。如果它对你有帮助，欢迎支持它的后续开发：

<a href="https://buymeacoffee.com/doweb"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40"></a>
