<h1 align="center">Byteplan</h1>

[English](README.md) · **Deutsch** · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt-BR.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

<p align="center"><b>Qwen3.8-Flash-Next, ein KI-Modell mit 180 Milliarden Parametern, läuft auf deinem Mac</b><br>
Gleiche Qualität wie llama.cpp, 2× schneller beim Bearbeiten von Code, Agent-Chats starten 18× früher · kostenlos und Open Source</p>

Byteplan bringt **[Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)** auf einen Mac mit Apple Silicon. Es chattet, schreibt Code, liest Bilder und arbeitet mit deinen Apps und Coding-Agenten zusammen. Nichts verlässt deinen Mac. Mit einem einzigen Befehl laufen auch [andere Modelle](#andere-modelle) von Hugging Face.

## Wie schnell ist es?

Gemessen auf einem MacBook Pro M3 Max mit 64 GB, im Vergleich zum normalen [llama.cpp](https://github.com/ggml-org/llama.cpp) mit derselben Modelldatei und demselben Helfer. Ein Token ist etwa ¾ eines Wortes.

| | llama.cpp | **Byteplan** |
|---|---:|---:|
| Code bearbeiten (wiederholt viel aus deiner Datei) | 76 tokens/s | **162 tokens/s** |
| Code umbauen in einem Agenten | 69 tokens/s | **108 tokens/s** |
| Neuen Code schreiben | 74 tokens/s | **80 tokens/s** |
| Text schreiben | 51 tokens/s | **57 tokens/s** |
| Langen Prompt einlesen | 440 tokens/s | **454 tokens/s** |
| Neuer Agent-Chat: Wartezeit bis zum ersten Wort | 3.8 s | **0.2 s** |

Seit dem 11.10.2026 liest Byteplan lange Prompts 26 % schneller, mit denselben Antworten, und liegt damit gleichauf mit sushi ([Details](docs/COMPARISON.md#measured-on-the-same-mac-byteplan-vs-sushi)). Diese Tabelle wird neu gemessen.

**Gleiche Qualität wie llama.cpp:** dieselbe Modelldatei, kein Gewicht verändert, keine Arbeit ausgelassen. Prüft das Modell viele geratene Wörter auf einmal, rundet es minimal anders als beim Schreiben Wort für Wort. Deshalb weicht hin und wieder ein einzelnes Wort ab. llama.cpp macht das genauso: Sein eigener Helfer ändert 1 der 4 Testantworten, und Byteplan stimmt in 3 von 4 mit llama.cpp überein. Über 8.000 Tokens gemessen weichen beide gleich wenig ab ([Details](docs/HOW_IT_WORKS.md#1-guess-ahead-check-exactly-mtp--n-gram-drafts)). Byteplan ist schneller, wo sich Text wiederholt und wenn ein Chat startet. Bei ganz neuem Text ist es 8 bis 12 % schneller. Alle Zahlen, die Methode und wie du selbst auf deinem Mac misst: [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

<p align="center"><a href="https://buymeacoffee.com/doweb"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50"></a><br>
<sub>Byteplan ist kostenlos. Wenn es dir Zeit spart, hilft mir ein Kaffee, es weiter zu verbessern.</sub></p>

## Was du brauchst

| | |
|---|---|
| **Mac** | Apple Silicon (M1 oder neuer). Getestet: MacBook Pro M3 Max. Chips mit weniger Speicherbandbreite (Pro, Basis-M) sind langsamer. |
| **Arbeitsspeicher** | **64 GB** (getestet). 48 GB sollten mit `--spar 256` reichen (noch nicht getestet). Weniger: nur [kleinere Modelle](#andere-modelle). |
| **Speicherplatz** | 150 GB frei während der Einrichtung, danach etwa 70 GB (+37 GB für `--spar`). |
| **Werkzeuge** | Xcode-Kommandozeilentools und [Homebrew](https://brew.sh). Der Installer sagt dir, wenn etwas fehlt. |

### Wie viel Text es sich merkt (Kontext)

| Kontext | etwa | Mac mit 64 GB | Mac mit 48 GB (ungetestet) |
|---|---|---|---|
| 64k Tokens (Standard) | 100 Seiten | `bin/chat` | `bin/chat --spar 256` |
| 96k Tokens | 145 Seiten | `bin/chat --long` | `bin/chat --long --spar 256` |
| 256k Tokens (das Maximum des Modells) | 390 Seiten | `bin/chat --max --spar 358` | passt nicht |

Mehr Kontext braucht mehr Arbeitsspeicher (~1.4 GB pro zusätzliche 32k Tokens). Wird ein Chat länger als der Kontext, fällt der älteste Teil heraus. Die Weboberfläche kann ihn für dich zusammenfassen (Compact).

## Installation

### Lass deine KI das einrichten

Du nutzt einen KI-Coding-Assistenten (Claude Code, Cursor, Codex, ...)? Füge dort diesen Text ein:

```text
Set up Byteplan on this Mac for me: https://github.com/do-web/byteplan - follow docs/AI_SETUP.md in that repository.
```

### Oder mach es selbst

Öffne die App Terminal und füge diese Zeilen einzeln ein:

```sh
xcode-select --install                 # einmalig; überspringen, wenn "already installed" kommt
brew install git cmake node uv
git clone https://github.com/do-web/byteplan && cd byteplan
./install.sh                           # Mac mit 64 GB (48 GB: ./install.sh --spar)
```

Der Installer baut Byteplan (ein paar Minuten), lädt das Modell herunter (etwa 70 GB) und bereitet es vor. Bricht der Download ab, starte `./install.sh` noch einmal: Es macht dort weiter, wo es aufgehört hat.

## Benutzung

```sh
bin/chat
```

Warte, bis gemeldet wird, dass das Modell geladen ist (die Seite im Browser zeigt einen Fortschrittsbalken). Dann öffne **http://127.0.0.1:8080**. Beenden mit `Ctrl-C`.

- **Deine Apps:** Leg einen „OpenAI-compatible“-Anbieter an, mit der Basis-URL **`http://127.0.0.1:8080/v1`** (beliebiger API-Key, beliebiger Modellname). Coding-Agenten: siehe unten.
- **Das Modell an deinen Dateien arbeiten lassen:** `bin/chat --agent` gibt dem Chat Werkzeuge, um Dateien zu lesen und zu schreiben und Befehle auszuführen. Nur auf deinem eigenen Mac.
- **Bilder:** Häng sie im Chat an. Das erste Bild dauert ein paar Sekunden länger.
- **Zu wenig Arbeitsspeicher?** `bin/chat --spar 410` (oder 358, 256) hält weniger Experten im Speicher. Die Antworten bleiben exakt gleich, es wird nur langsamer ([Zahlen](docs/HOW_IT_WORKS.md#3-expert-pool-for-smaller-macs---spar-s)). Dafür einmal `./install.sh --spar` ausführen.
- **Weniger Ablehnungen:** `bin/chat --uncensored`, standardmäßig aus ([was es macht](docs/UNCENSORED.md)).

### Coding-Agenten (Claude Code, Codex)

Agenten schicken lange Anweisungen und Werkzeuglisten mit. Gib ihnen deshalb mehr Kontext und starte `bin/chat --long` (96k) oder `bin/chat --max --spar 358` (256k). Die erste Antwort dauert 30 bis 70 Sekunden, weil das Modell diese Anweisungen erst einliest (Codex etwa 12.000 Tokens, Claude Code etwa 26.000, mit vielen MCP-Servern mehr). Byteplan legt sie auf der SSD ab. Die nächste Sitzung startet deshalb nach wenigen Sekunden, auch nach einem Neustart (Claude Code mit 51.000 Tokens: etwa 90 s beim ersten Mal, 25 s nach einem Neustart).

**Claude Code**, in einem zweiten Terminal:

```sh
export ANTHROPIC_BASE_URL=http://127.0.0.1:8080 ANTHROPIC_AUTH_TOKEN=local
export ANTHROPIC_MODEL=qwen3.8-flash-next ANTHROPIC_DEFAULT_HAIKU_MODEL=qwen3.8-flash-next
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=90000    # knapp unter bin/chat --long (98.304): Claude Code zählt Tokens anders
claude
```

Meldet Claude Code, dass die Anfrage größer ist als der Kontext, liegt das an vielen MCP-Servern: Sie machen jede Anfrage länger. Nutze dann `bin/chat --max --spar 358` und `CLAUDE_CODE_MAX_CONTEXT_TOKENS=240000` oder starte `claude --strict-mcp-config`, also ohne die MCP-Server.

**Codex**: Trag das in `~/.codex/config.toml` ein und starte dann `codex`:

```toml
model = "qwen3.8-flash-next"
model_provider = "byteplan"
model_context_window = 90000

[model_providers.byteplan]
name = "Byteplan"
base_url = "http://127.0.0.1:8080/v1"
wire_api = "responses"
```

## Andere Modelle

```sh
bin/run Qwen/Qwen3-8B-GGUF                         # ein fertiges GGUF-Modell
bin/run https://huggingface.co/Qwen/Qwen3-8B       # Original-Gewichte: werden einmal umgewandelt
bin/run qwen3 8b                                   # Name unklar? Zeigt passende Treffer
```

`bin/run` lädt das Modell herunter und wählt die beste Größe, die in deinen Arbeitsspeicher passt (8-Bit, wenn es reicht: fast kein Qualitätsverlust). Original-Gewichte wandelt es beim ersten Mal in GGUF um. Danach startet dieselbe Weboberfläche. Die Größe kannst du auch selbst wählen, mit `:Q4_K_M` (schneller) oder `:Q8_0` (genauer). Willst du nur andere Modelle nutzen, führe vorher `./install.sh --no-model` aus.

Andere Modelle bekommen die allgemeinen Beschleunigungen (Raten und Prüfen mit Entwürfen, schnellere Agent-Starts, Bilder nur bei Bedarf, Speicherwächter). Der Expertenpool und der -O1-Compiler sind nur für Qwen3.8-Flash-Next gebaut.

### Welches Modell für meinen Mac?

| Arbeitsspeicher | Modell | Starten mit | Größe | Gut für |
|---|---|---|---:|---|
| 16 GB | Gemma 4 E4B | `bin/run unsloth/gemma-4-E4B-it-qat-GGUF` | 3.9 GB | Chat im Alltag, Bilder |
| 16 GB | Qwen3.5 4B | `bin/run unsloth/Qwen3.5-4B-GGUF` | 4.2 GB | kleine Code-Aufgaben, Werkzeuge |
| 24 GB | MiMo-V2.6 Distill 9B | `bin/run ggml-org/MiMo-V2.6-Distill-Qwen-9B-GGUF` | 8.9 GB | Code und Agenten |
| 24 GB | Gemma 4 12B | `bin/run unsloth/gemma-4-12B-it-qat-GGUF` | 6.3 GB | Chat, Bilder |
| 32 GB | Qwen3.6 35B-A3B | `bin/run unsloth/Qwen3.6-35B-A3B-GGUF` | 16.8 GB | schneller Allrounder (MoE) |
| 32 GB | Qwen3.8 27B | `bin/run unsloth/Qwen3.8-27B-GGUF` | 16.4 GB | stärkstes Code-Modell, das reinpasst, langsamer |
| 48 GB | Qwen3.8 27B | `bin/run unsloth/Qwen3.8-27B-GGUF` | 27.1 GB | dasselbe in 8-Bit |
| 64 GB | **Qwen3.8-Flash-Next** | `bin/chat` | 37 GB | **das Hauptmodell: beste Qualität** |
| 64 GB | Qwen3.6 35B-A3B | `bin/run ggml-org/Qwen3.6-35B-A3B-GGUF` | 34.4 GB | schnelles MoE, 8-Bit, mit MTP-Helfer |
| 96–128 GB | Laguna S 2.1 118B-A8B | `bin/run unsloth/Laguna-S-2.1-GGUF` | 68–91 GB | Coding mit Agenten |

Die Größe ist das, was `bin/run` auf dem jeweiligen Mac wählt. **MoE**-Modelle („A3B“ = 3 Milliarden aktive Parameter pro Wort) sind auf einem Mac schnell. **Dichte** Modelle (dense) lesen für jedes Wort alle ihre Gewichte. Deshalb sind sie langsamer, aber oft schlauer. Alle Modelle oben können den Anfang von Agent-Chats auf der SSD ablegen. Repos mit einer `mtp-`-Datei bekommen außerdem den MTP-Helfer.

**Lohnt sich nicht:** dichte Modelle mit 70B+ (langsam auf einem Mac und schwächer als Qwen3.8 27B), MoE-Modelle mit 200B+, auf 1 bis 3 Bit zusammengequetscht, ein 35B mit 2 Bit statt eines 9B mit 8 Bit und Repos, die keine Chat-Modelle sind (Namen mit `-Base`, Gemma ohne `-it`, Modelle für OCR, gesprochene Sprache oder Embeddings).

## Byteplan und andere Projekte

| | Byteplan | [sushi](https://github.com/beamivalice/sushi) | [Strata](https://github.com/Niko1221/Strata) |
|---|---|---|---|
| Läuft auf | Mac | Mac | Windows-/Linux-PC mit Gaming-Grafikkarte |
| Qualität der unveränderten Engine | ja, nur die Rundung weicht ab (wie beim eigenen Helfer von llama.cpp) | die Standardeinstellungen sind verlustbehaftet (Attention und KV-Cache quantisiert) | nicht geprüft |
| Code bearbeiten / neuer Text (tokens/s, gleicher M3 Max, 2-Bit) | **143** / 55 bis 77 | 99 / 52 bis 75 | (nur PC) |
| Prompt einlesen (tokens/s) | **647 bis 658** | 630 bis 649 | (nur PC) |
| Neuer Agent-Chat startet nach | **0.2 s** | 2.7 s | (nur PC) |

Auf diesem Mac liest Byteplan lange Prompts 1 bis 3 % schneller als sushi und schreibt neuen Text 2 bis 6 % schneller. Byteplan bearbeitet Code 44 % schneller, startet Agent-Chats 13× früher und hält die Qualität von llama.cpp. Details und Quellen: [docs/COMPARISON.md](docs/COMPARISON.md).

## Wie funktioniert das?

- **Raten, dann prüfen:** Ein kleiner Helfer rät die nächsten Wörter, und Byteplan übernimmt wahrscheinlichen Text aus dem Gespräch (bei Code-Änderungen wiederholt sich viel). Das große Modell prüft alle Vorschläge auf einmal und behält nur, was es sowieso geschrieben hätte.
- **Bereit für Agenten:** Den langen Anfang, den Agent-Apps bei jedem Chat mitschicken, behält Byteplan im Speicher und auf der SSD. Ein neuer Chat startet deshalb sofort, auch nach einem Neustart.
- **Weniger Schritte auf der GPU:** Kleine GPU-Schritte werden zusammengelegt und so umgeschrieben, dass sie genau wie vorher runden.
- **Expertenpool:** Das Modell hat 512 Experten pro Schicht und nutzt 10 pro Wort. Mit `--spar` bleiben nur die meistgenutzten im Speicher. Der Rest kommt erst von der SSD, wenn er gebraucht wird.
- **Speicherwächter:** Prüft vor dem Start den freien Arbeitsspeicher und stoppt das Modell, bevor dein Mac anfängt auszulagern.

Mehr: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) · die Änderungen an llama.cpp: [docs/PATCHES.md](docs/PATCHES.md)

## Etwas klappt nicht?

- **„not enough free RAM“**: Schließ andere Apps (Browser und Docker brauchen viel) oder nutze `--spar 410`.
- **„stopped by the memory watchdog“**: Gleiche Lösung. Der Wächter hat das Modell gestoppt, bevor macOS langsam wurde.
- **„swap in use“**: macOS hält noch ausgelagerten Speicher von vorher fest. Starte den Mac neu.
- **Die Seite zeigt länger „Loading model“:** Beim ersten Start normal (37 GB müssen gelesen werden). Spätere Starts gehen schneller.
- **`./install.sh` ist abgebrochen:** Starte es noch einmal, es macht weiter. Das Log steht in `install.log`.

Kommst du nicht weiter? Öffne ein [Issue](https://github.com/do-web/byteplan/issues) und nenne deinen Mac, den Arbeitsspeicher und die letzten Zeilen aus dem Terminal.

## Danksagung und Lizenz

Byteplan baut auf [llama.cpp](https://github.com/ggml-org/llama.cpp) (MIT) auf, auf dem Modell des [Qwen](https://huggingface.co/Qwen)-Teams, den quantisierten Dateien von [ISTA-DASLab](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF), dem MTP-Helfer von [Joakimpalm-Zen](https://huggingface.co/Joakimpalm-Zen/Qwen3.8-Flash-Next-MTP-GGUF) und der Ablehnungsrichtung (refusal direction) von [Cudecnik](https://huggingface.co/Cudecnik/Qwen3.8-Flash-Next-refusal-projection). Byteplan ist Open Source unter der [MIT-Lizenz](LICENSE). Das Modell hat eine eigene Lizenz (Qwen Community License 1.0, siehe [NOTICE](NOTICE)). Dieses Repository enthält keine Modellgewichte.

## Unterstützung

Byteplan ist kostenlos und Open Source. Wenn es dir nützt, kannst du die Weiterentwicklung unterstützen:

<a href="https://buymeacoffee.com/doweb"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40"></a>
