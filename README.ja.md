<h1 align="center">Byteplan</h1>

[English](README.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt-BR.md) · [简体中文](README.zh-CN.md) · **日本語**

<p align="center"><b>1800億パラメータのAIモデル Qwen3.8-Flash-Next を、あなたのMacで動かす</b><br>
品質はllama.cppと同じ。コード編集は2倍速く、エージェントのチャットは18倍早く始まります · 無料のオープンソース</p>

Byteplanは、Apple Silicon搭載のMacで **[Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)** を動かします。チャットをして、コードを書き、画像を読み、あなたのアプリやコーディングエージェントとも連携します。データがMacの外に出ることはありません。Hugging Faceの[ほかのモデル](#ほかのモデル)も、コマンドひとつで動かせます。

## どのくらい速い？

MacBook Pro M3 Max（64 GB）で測りました。比べた相手は、同じモデルファイルと同じ補助モデルを使った素の [llama.cpp](https://github.com/ggml-org/llama.cpp) です。1トークンは英単語のおよそ¾です。

| | llama.cpp | **Byteplan** |
|---|---:|---:|
| コードを編集する（ファイルの多くをそのまま書き写す） | 76 tokens/s | **162 tokens/s** |
| エージェントでコードをリファクタリングする | 69 tokens/s | **108 tokens/s** |
| 新しいコードを書く | 74 tokens/s | **80 tokens/s** |
| 文章を書く | 51 tokens/s | **57 tokens/s** |
| 長いプロンプトを読み込む | 440 tokens/s | **454 tokens/s** |
| 新しいエージェントチャット：最初の言葉が出るまでの待ち時間 | 3.8 s | **0.2 s** |

2026年10月11日から、Byteplanは同じ答えのまま長いプロンプトを26 %速く読み、sushiと同等になりました（[詳細](docs/COMPARISON.md#measured-on-the-same-mac-byteplan-vs-sushi)）。この表は測り直します。

**品質はllama.cppと同じです**。同じモデルファイルを使い、重みは一切変えず、計算も省きません。推測した複数の単語をまとめて確かめると、一語ずつ書くときとごくわずかに丸め方が変わるため、ときどき一語だけ違うことがあります。llama.cppでも同じで、自前の補助モデルを使うと4つのテスト回答のうち1つが変わります。Byteplanの答えは4つのうち3つがllama.cppと同じです。8,000トークンで測ると、どちらのずれも同じくらい小さいことが分かります（[詳細](docs/HOW_IT_WORKS.md#1-guess-ahead-check-exactly-mtp--n-gram-drafts)）。Byteplanが速いのは、同じ文章がくり返される場面と、チャットを始めるときです。まったく新しい文章では、8〜12 %速くなります。すべての数値、測り方、自分のMacで測る方法：[docs/BENCHMARKS.md](docs/BENCHMARKS.md)

<p align="center"><a href="https://buymeacoffee.com/doweb"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50"></a><br>
<sub>Byteplanは無料です。時間の節約になったなら、コーヒー1杯がこれからの改善の支えになります。</sub></p>

## 必要なもの

| | |
|---|---|
| **Mac** | Apple Silicon（M1以降）。テスト済み：MacBook Pro M3 Max。メモリ帯域の狭いチップ（Proや無印のM）だと遅くなります。 |
| **メモリ** | **64 GB**（テスト済み）。48 GBなら `--spar 256` で動くはずです（まだテストしていません）。それより少ない場合は[小さめのモデル](#ほかのモデル)だけ使えます。 |
| **ディスク** | セットアップ中は150 GBの空きが必要で、終わったあとは約70 GBです（`--spar` を使うと+37 GB）。 |
| **ツール** | Xcodeコマンドラインツールと [Homebrew](https://brew.sh)。足りないものがあれば、インストーラーが教えてくれます。 |

### どれだけの文章を覚えておけるか（コンテキスト）

| コンテキスト | 目安 | 64 GBのMac | 48 GBのMac（未テスト） |
|---|---|---|---|
| 64kトークン（標準） | 100ページ | `bin/chat` | `bin/chat --spar 256` |
| 96kトークン | 145ページ | `bin/chat --long` | `bin/chat --long --spar 256` |
| 256kトークン（モデルの上限） | 390ページ | `bin/chat --max --spar 358` | 収まらない |

コンテキストを増やすほど、メモリが必要になります（32kトークン増えるごとに約1.4 GB）。チャットがコンテキストより長くなると、いちばん古い部分から消えていきます。Web UIでは、その部分を要約することもできます（Compact）。

## インストール

### AIにセットアップしてもらう

AIコーディングアシスタント（Claude Code、Cursor、Codex など）を使っていますか？ 次の文を英語のまま貼り付けてください。

```text
Set up Byteplan on this Mac for me: https://github.com/do-web/byteplan - follow docs/AI_SETUP.md in that repository.
```

### 自分でやる

「ターミナル」アプリを開いて、次の行を1行ずつ貼り付けてください。

```sh
xcode-select --install                 # 初回だけ。"already installed" と出たら飛ばしてOK
brew install git cmake node uv
git clone https://github.com/do-web/byteplan && cd byteplan
./install.sh                           # 64 GBのMac (48 GBなら ./install.sh --spar)
```

インストーラーがByteplanをビルドし（数分）、モデルをダウンロードして（約70 GB）、使える状態に準備します。ダウンロードが止まったら、もう一度 `./install.sh` を実行してください。止まったところから続けます。

## 使い方

```sh
bin/chat
```

モデルの読み込み完了が表示されるまで待ち（ブラウザのページには進み具合のバーが出ます）、**http://127.0.0.1:8080** を開きます。止めるときは `Ctrl-C` です。

- **アプリから使う**：「OpenAI互換（OpenAI-compatible）」のプロバイダーを追加し、ベースURLに **`http://127.0.0.1:8080/v1`** を指定します（APIキーもモデル名も何でもかまいません）。コーディングエージェントについては、下を見てください。
- **モデルにファイルを扱わせる**：`bin/chat --agent` を使うと、チャットがファイルを読み書きしたり、コマンドを実行したりできます。自分のMacでだけ使ってください。
- **画像**：チャットに添付するだけです。最初の1枚だけ、数秒ほど長くかかります。
- **メモリが足りない？** `bin/chat --spar 410`（または 358、256）を使うと、メモリに置くエキスパートを減らせます。答えはまったく同じままで、遅くなるだけです（[数値](docs/HOW_IT_WORKS.md#3-expert-pool-for-smaller-macs---spar-s)）。事前に一度だけ `./install.sh --spar` が必要です。
- **回答拒否を減らす**：`bin/chat --uncensored` を使います。標準ではオフです（[何をするのか](docs/UNCENSORED.md)）。

### コーディングエージェント（Claude Code、Codex）

エージェントは長い指示やツールの一覧を送ってくるので、コンテキストを増やしてください：`bin/chat --long`（96k）か `bin/chat --max --spar 358`（256k）で起動します。最初の答えは、モデルがその指示を読むあいだ30〜70秒かかります（Codexで約12,000トークン、Claude Codeで約26,000トークン。MCPサーバーが多いともっと増えます）。ByteplanはそれをSSDに保存しておくので、次のセッションは再起動したあとでも数秒で始まります（Claude Codeで51,000トークンの場合、初回は約90秒、再起動後は25秒）。

**Claude Code**：2つ目のターミナルで、次を実行します。

```sh
export ANTHROPIC_BASE_URL=http://127.0.0.1:8080 ANTHROPIC_AUTH_TOKEN=local
export ANTHROPIC_MODEL=qwen3.8-flash-next ANTHROPIC_DEFAULT_HAIKU_MODEL=qwen3.8-flash-next
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=90000    # bin/chat --long（98,304）より少し小さく：Claude Codeはトークンの数え方が違う
claude
```

リクエストがコンテキストの大きさを超えていると表示されたら、たくさんのMCPサーバーがリクエストを毎回長くしています。`bin/chat --max --spar 358` と `CLAUDE_CODE_MAX_CONTEXT_TOKENS=240000` を使うか、MCPサーバーなしで `claude --strict-mcp-config` を起動してください。

**Codex**：`~/.codex/config.toml` に次を追加してから、`codex` を実行します。

```toml
model = "qwen3.8-flash-next"
model_provider = "byteplan"
model_context_window = 90000

[model_providers.byteplan]
name = "Byteplan"
base_url = "http://127.0.0.1:8080/v1"
wire_api = "responses"
```

## ほかのモデル

```sh
bin/run Qwen/Qwen3-8B-GGUF                         # すぐ使えるGGUFモデル
bin/run https://huggingface.co/Qwen/Qwen3-8B       # 元の重み: 最初に一度だけ変換
bin/run qwen3 8b                                   # 名前があいまいでもOK: 候補を表示
```

`bin/run` はモデルをダウンロードし、メモリに収まるいちばん良いサイズを選び（収まるなら8-bit。品質はほとんど落ちません）、元の重みなら最初の1回だけGGUFに変換して、いつもと同じWeb UIを起動します。サイズを自分で選ぶなら、モデル名の後ろに `:Q4_K_M`（速い）か `:Q8_0`（より正確）を付けます。ほかのモデルだけを使いたいなら、先に `./install.sh --no-model` を実行してください。

ほかのモデルでも、共通の高速化は効きます（予想して確かめる下書き、エージェントの素早い開始、必要なときだけ読み込む画像処理、メモリガード）。エキスパートプールと -O1 コンパイラーは、Qwen3.8-Flash-Next専用です。

### 自分のMacにはどのモデル？

| メモリ | モデル | 起動コマンド | サイズ | 向いている用途 |
|---|---|---|---:|---|
| 16 GB | Gemma 4 E4B | `bin/run unsloth/gemma-4-E4B-it-qat-GGUF` | 3.9 GB | ふだんのチャット、画像 |
| 16 GB | Qwen3.5 4B | `bin/run unsloth/Qwen3.5-4B-GGUF` | 4.2 GB | 小さなコード作業、ツール |
| 24 GB | MiMo-V2.6 Distill 9B | `bin/run ggml-org/MiMo-V2.6-Distill-Qwen-9B-GGUF` | 8.9 GB | コードとエージェント |
| 24 GB | Gemma 4 12B | `bin/run unsloth/gemma-4-12B-it-qat-GGUF` | 6.3 GB | チャット、画像 |
| 32 GB | Qwen3.6 35B-A3B | `bin/run unsloth/Qwen3.6-35B-A3B-GGUF` | 16.8 GB | 速い万能型（MoE） |
| 32 GB | Qwen3.8 27B | `bin/run unsloth/Qwen3.8-27B-GGUF` | 16.4 GB | 収まる中でいちばん強いコーダー、ただし遅め |
| 48 GB | Qwen3.8 27B | `bin/run unsloth/Qwen3.8-27B-GGUF` | 27.1 GB | 同じモデルの8-bit版 |
| 64 GB | **Qwen3.8-Flash-Next** | `bin/chat` | 37 GB | **メインモデル：品質はいちばん** |
| 64 GB | Qwen3.6 35B-A3B | `bin/run ggml-org/Qwen3.6-35B-A3B-GGUF` | 34.4 GB | 速いMoE、8-bit、MTP補助モデル付き |
| 96〜128 GB | Laguna S 2.1 118B-A8B | `bin/run unsloth/Laguna-S-2.1-GGUF` | 68〜91 GB | エージェントによるコーディング |

サイズは、そのMacで `bin/run` が選ぶものです。**MoE** モデル（「A3B」は、1語ごとに30億パラメータだけが動くという意味）はMacで速く動きます。**dense**（密）モデルは1語ごとにすべての重みを読むので、遅くなりますが、賢いことが多いです。上のモデルはすべて、エージェントチャットの始まりの部分をSSDに保存できます。`mtp-` ファイルがあるリポジトリでは、MTP補助モデルも使えます。

**おすすめしないもの**：70B以上のdenseモデル（Macでは遅く、Qwen3.8 27Bより弱い）、1〜3 bitまで詰め込んだ200B以上のMoEモデル、8-bitの9Bの代わりに2-bitの35Bを使うこと、チャットモデルではないリポジトリ（名前に `-Base` が付くもの、`-it` が付かないGemma、OCR、音声、埋め込みのモデル）。

## Byteplanとほかのプロジェクト

| | Byteplan | [sushi](https://github.com/beamivalice/sushi) | [Strata](https://github.com/Niko1221/Strata) |
|---|---|---|---|
| 動く環境 | Mac | Mac | ゲーム用グラフィックカードを積んだWindows/Linux PC |
| 手を加えていないエンジンと同じ品質 | はい、違うのは丸めだけ（llama.cpp自前の補助モデルと同じ） | 初期設定は品質が落ちる（attentionとKVキャッシュを量子化） | 未確認 |
| コード編集 / 新しい文章（tokens/s、同じM3 Max、2-bit） | **143** / 55〜77 | 99 / 52〜75 | （PCのみ） |
| プロンプトを読み込む（tokens/s） | **647〜658** | 630〜649 | （PCのみ） |
| 新しいエージェントチャットが始まるまで | **0.2 s** | 2.7 s | （PCのみ） |

このMacでは、長いプロンプトの読み込みはByteplanのほうがsushiより1〜3 %速く、新しい文章も2〜6 %速く書きます。コード編集は44 %速く、エージェントのチャットは13倍早く始まり、llama.cppと同じ品質を保ちます。詳細と出典：[docs/COMPARISON.md](docs/COMPARISON.md)

## どういうしくみ？

- **予想して、確かめる**：小さな補助モデルが次の言葉を予想し、Byteplanは会話から出てきそうな文章をコピーします（コード編集では同じ文章がよくくり返されます）。大きなモデルはすべての予想をまとめて確かめ、もともと自分が書いたはずの部分だけを残します。
- **エージェント向けの準備**：エージェントアプリがチャットのたびに送る長い前置きをメモリとSSDに残しておくので、再起動したあとでも新しいチャットがすぐに始まります。
- **GPUの処理ステップを減らす**：GPUの小さな処理をまとめ、数値の丸め方が以前とまったく同じになるように書き直しています。
- **エキスパートプール**：このモデルは1層あたり512個のエキスパートを持ち、1語ごとに10個を使います。`--spar` を使うと、よく使うものだけをメモリに置き、残りは必要になったその時にSSDから読み込みます。
- **メモリガード**：起動前に空きメモリを確認し、Macがスワップを始める前にモデルを止めます。

詳しくは：[docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) · llama.cppへの変更点：[docs/PATCHES.md](docs/PATCHES.md)

## うまくいかないときは？

- **"not enough free RAM"**：ほかのアプリを閉じるか（ブラウザやDockerは多くのメモリを使います）、`--spar 410` を使ってください。
- **"stopped by the memory watchdog"**：対処は同じです。macOSが重くなる前に、ガードがモデルを止めました。
- **"swap in use"**：前に使ったスワップのメモリを、macOSがまだ抱えています。Macを再起動してください。
- **ページにしばらく "Loading model" と出ている**：初回の起動では普通です（37 GBを読み込むため）。2回目からはもっと速くなります。
- **`./install.sh` が止まった**：もう一度実行してください。続きから再開します。ログは `install.log` にあります。

それでも解決しないときは、Macの機種、メモリ容量、ターミナルの最後の数行を添えて [issue](https://github.com/do-web/byteplan/issues) を作成してください。

## クレジットとライセンス

Byteplanは、次のものの上に成り立っています：[llama.cpp](https://github.com/ggml-org/llama.cpp)（MIT）、[Qwen](https://huggingface.co/Qwen) チームのモデル、[ISTA-DASLab](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) による量子化ファイル、[Joakimpalm-Zen](https://huggingface.co/Joakimpalm-Zen/Qwen3.8-Flash-Next-MTP-GGUF) によるMTP補助モデル、[Cudecnik](https://huggingface.co/Cudecnik/Qwen3.8-Flash-Next-refusal-projection) による拒否方向（refusal direction）。Byteplanは [MITライセンス](LICENSE) のもとで公開されているオープンソースです。モデルには独自のライセンスがあります（Qwen Community License 1.0、[NOTICE](NOTICE) を参照）。このリポジトリには、モデルの重みは含まれていません。

## サポート

Byteplan は無料のオープンソースです。役に立ったら、開発を支援していただけるとうれしいです：

<a href="https://buymeacoffee.com/doweb"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40"></a>
