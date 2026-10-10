<h1 align="center">Byteplan</h1>

[English](README.md) · [Deutsch](README.de.md) · [Español](README.es.md) · **Français** · [Português](README.pt-BR.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

<p align="center"><b>Faites tourner Qwen3.8-Flash-Next, un modèle d'IA de 180 milliards de paramètres, sur votre Mac</b><br>
La même qualité que llama.cpp, 2× plus rapide quand il modifie du code, les chats d'agent démarrent 18× plus tôt · gratuit et open source</p>

Byteplan fait tourner **[Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)** sur un Mac avec Apple Silicon. Il discute, écrit du code, lit des images et fonctionne avec vos apps et vos agents de code. Rien ne quitte votre Mac. Il peut aussi faire tourner [d'autres modèles](#autres-modèles) de Hugging Face avec une seule commande.

## Quelle est sa vitesse ?

Mesuré sur un MacBook Pro M3 Max avec 64 GB, face à [llama.cpp](https://github.com/ggml-org/llama.cpp) sans modification, avec le même fichier de modèle et le même petit modèle d'aide. Un token correspond à environ ¾ d'un mot.

| | llama.cpp | **Byteplan** |
|---|---:|---:|
| Modifie du code (reprend une grande partie de votre fichier) | 76 tokens/s | **162 tokens/s** |
| Refactorise du code dans un agent | 69 tokens/s | **108 tokens/s** |
| Écrit du nouveau code | 74 tokens/s | **80 tokens/s** |
| Écrit du texte | 51 tokens/s | **57 tokens/s** |
| Lit un long prompt | 440 tokens/s | **454 tokens/s** |
| Nouveau chat d'agent : attente avant le premier mot | 3.8 s | **0.2 s** |

Depuis le 11/10/2026, Byteplan lit les longs prompts 26 % plus vite avec les mêmes réponses, au niveau de sushi ([détails](docs/COMPARISON.md#measured-on-the-same-mac-byteplan-vs-sushi)). Ce tableau sera mesuré à nouveau.

**La même qualité que llama.cpp :** le même fichier de modèle, aucun poids modifié, aucun calcul sauté. En vérifiant plusieurs mots devinés d'un coup, le modèle arrondit très légèrement autrement qu'en écrivant mot par mot, donc il arrive qu'un mot change. llama.cpp fait de même : son propre assistant change 1 des 4 réponses de test, et les réponses de Byteplan correspondent à celles de llama.cpp dans 3 cas sur 4. Mesuré sur 8 000 tokens, les deux s'écartent aussi peu l'un que l'autre ([détails](docs/HOW_IT_WORKS.md#1-guess-ahead-check-exactly-mtp--n-gram-drafts)). Byteplan est plus rapide quand le texte se répète et au début d'un chat. Pour un texte entièrement nouveau, il va 8 à 12 % plus vite. Tous les chiffres, la méthode et comment mesurer sur votre Mac : [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

<p align="center"><a href="https://buymeacoffee.com/doweb"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50"></a><br>
<sub>Byteplan est gratuit. S'il vous fait gagner du temps, un café m'aide à continuer de l'améliorer.</sub></p>

## Ce qu'il vous faut

| | |
|---|---|
| **Mac** | Apple Silicon (M1 ou plus récent). Testé : MacBook Pro M3 Max. Les puces avec moins de bande passante mémoire (Pro, M de base) sont plus lentes. |
| **Mémoire** | **64 GB** (testé). 48 GB devraient suffire avec `--spar 256` (pas encore testé). Moins : seulement des [modèles plus petits](#autres-modèles). |
| **Disque** | 150 GB libres pendant l'installation, environ 70 GB ensuite (+37 GB pour `--spar`). |
| **Outils** | Les outils en ligne de commande Xcode et [Homebrew](https://brew.sh). L'installateur vous prévient s'il manque quelque chose. |

### Combien de texte il garde en tête (contexte)

| Contexte | environ | Mac avec 64 GB | Mac avec 48 GB (non testé) |
|---|---|---|---|
| 64k tokens (par défaut) | 100 pages | `bin/chat` | `bin/chat --spar 256` |
| 96k tokens | 145 pages | `bin/chat --long` | `bin/chat --long --spar 256` |
| 256k tokens (le maximum du modèle) | 390 pages | `bin/chat --max --spar 358` | ne rentre pas |

Plus de contexte demande plus de mémoire (~1.4 GB par tranche de 32k tokens en plus). Quand un chat dépasse le contexte, la partie la plus ancienne est oubliée. L'interface web peut la résumer pour vous (Compact).

## Installation

### Laissez votre IA l'installer

Vous utilisez un assistant de code IA (Claude Code, Cursor, Codex, ...) ? Collez-lui ceci :

```text
Set up Byteplan on this Mac for me: https://github.com/do-web/byteplan - follow docs/AI_SETUP.md in that repository.
```

### Ou faites-le vous-même

Ouvrez l'app Terminal et collez ces lignes une par une :

```sh
xcode-select --install                 # une seule fois ; à sauter s'il affiche "already installed"
brew install git cmake node uv
git clone https://github.com/do-web/byteplan && cd byteplan
./install.sh                           # Mac avec 64 GB (48 GB : ./install.sh --spar)
```

L'installateur compile Byteplan (quelques minutes), télécharge le modèle (environ 70 GB) et le prépare. Si le téléchargement s'arrête, relancez `./install.sh` : il reprend là où il s'était arrêté.

## Utilisation

```sh
bin/chat
```

Attendez qu'il indique que le modèle est chargé (la page du navigateur affiche une barre de progression), puis ouvrez **http://127.0.0.1:8080**. Arrêtez-le avec `Ctrl-C`.

- **Vos apps :** ajoutez un fournisseur "OpenAI-compatible" avec l'URL de base **`http://127.0.0.1:8080/v1`** (n'importe quelle clé API, n'importe quel nom de modèle). Agents de code : voir plus bas.
- **Laisser le modèle travailler sur vos fichiers :** `bin/chat --agent` donne au chat des outils pour lire et écrire des fichiers et lancer des commandes. Uniquement sur votre propre Mac.
- **Images :** joignez-les dans le chat. La première image prend quelques secondes de plus.
- **Pas assez de mémoire ?** `bin/chat --spar 410` (ou 358, 256) garde moins d'experts en mémoire. Les réponses restent exactement les mêmes, elles arrivent juste plus lentement ([chiffres](docs/HOW_IT_WORKS.md#3-expert-pool-for-smaller-macs---spar-s)). Il faut lancer `./install.sh --spar` une fois.
- **Moins de refus :** `bin/chat --uncensored`, désactivé par défaut ([ce que ça fait](docs/UNCENSORED.md)).

### Agents de code (Claude Code, Codex)

Les agents envoient de longues instructions et des listes d'outils. Donnez-leur donc plus de contexte : lancez `bin/chat --long` (96k) ou `bin/chat --max --spar 358` (256k). La première réponse prend 30 à 70 secondes, le temps que le modèle lise ces instructions (Codex environ 12 000 tokens, Claude Code environ 26 000 ; davantage avec de nombreux serveurs MCP). Byteplan les garde sur le SSD : la session suivante démarre donc en quelques secondes, même après un redémarrage (Claude Code avec 51 000 tokens : environ 90 s la première fois, 25 s après un redémarrage).

**Claude Code**, dans un deuxième terminal :

```sh
export ANTHROPIC_BASE_URL=http://127.0.0.1:8080 ANTHROPIC_AUTH_TOKEN=local
export ANTHROPIC_MODEL=qwen3.8-flash-next ANTHROPIC_DEFAULT_HAIKU_MODEL=qwen3.8-flash-next
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=90000    # un peu moins que bin/chat --long (98 304) : Claude Code compte les tokens autrement
claude
```

S'il indique que la requête dépasse la taille du contexte, c'est que de nombreux serveurs MCP rallongent chaque requête : utilisez `bin/chat --max --spar 358` et `CLAUDE_CODE_MAX_CONTEXT_TOKENS=240000`, ou lancez `claude --strict-mcp-config` sans ces serveurs.

**Codex** : ajoutez ceci à `~/.codex/config.toml`, puis lancez `codex` :

```toml
model = "qwen3.8-flash-next"
model_provider = "byteplan"
model_context_window = 90000

[model_providers.byteplan]
name = "Byteplan"
base_url = "http://127.0.0.1:8080/v1"
wire_api = "responses"
```

## Autres modèles

```sh
bin/run Qwen/Qwen3-8B-GGUF                         # un modèle GGUF prêt à l'emploi
bin/run https://huggingface.co/Qwen/Qwen3-8B       # poids d'origine : convertis une seule fois
bin/run qwen3 8b                                   # pas sûr du nom ? affiche les résultats proches
```

`bin/run` télécharge le modèle, choisit la meilleure taille qui tient dans votre mémoire (8-bit si ça rentre : presque aucune perte de qualité), convertit les poids d'origine en GGUF la première fois et lance la même interface web. Pour choisir la taille vous-même, ajoutez `:Q4_K_M` (plus rapide) ou `:Q8_0` (plus précis). Si vous voulez seulement d'autres modèles, lancez d'abord `./install.sh --no-model`.

Les autres modèles profitent des accélérations générales (brouillons devinés puis vérifiés, démarrage plus rapide des agents, images à la demande, garde-fou mémoire). La réserve d'experts et le compilateur -O1 sont faits uniquement pour Qwen3.8-Flash-Next.

### Quel modèle pour mon Mac ?

| Mémoire | Modèle | Lancer avec | Taille | Idéal pour |
|---|---|---|---:|---|
| 16 GB | Gemma 4 E4B | `bin/run unsloth/gemma-4-E4B-it-qat-GGUF` | 3.9 GB | chat au quotidien, images |
| 16 GB | Qwen3.5 4B | `bin/run unsloth/Qwen3.5-4B-GGUF` | 4.2 GB | petites tâches de code, outils |
| 24 GB | MiMo-V2.6 Distill 9B | `bin/run ggml-org/MiMo-V2.6-Distill-Qwen-9B-GGUF` | 8.9 GB | code et agents |
| 24 GB | Gemma 4 12B | `bin/run unsloth/gemma-4-12B-it-qat-GGUF` | 6.3 GB | chat, images |
| 32 GB | Qwen3.6 35B-A3B | `bin/run unsloth/Qwen3.6-35B-A3B-GGUF` | 16.8 GB | polyvalent et rapide (MoE) |
| 32 GB | Qwen3.8 27B | `bin/run unsloth/Qwen3.8-27B-GGUF` | 16.4 GB | le meilleur pour le code qui rentre, plus lent |
| 48 GB | Qwen3.8 27B | `bin/run unsloth/Qwen3.8-27B-GGUF` | 27.1 GB | le même, en 8-bit |
| 64 GB | **Qwen3.8-Flash-Next** | `bin/chat` | 37 GB | **le modèle principal : la meilleure qualité** |
| 64 GB | Qwen3.6 35B-A3B | `bin/run ggml-org/Qwen3.6-35B-A3B-GGUF` | 34.4 GB | MoE rapide, 8-bit, avec le modèle d'aide MTP |
| 96–128 GB | Laguna S 2.1 118B-A8B | `bin/run unsloth/Laguna-S-2.1-GGUF` | 68–91 GB | code agentique |

Les tailles sont celles que `bin/run` choisit sur ce Mac. Les modèles **MoE** ("A3B" = 3 milliards de paramètres actifs par mot) sont rapides sur un Mac ; les modèles **denses** lisent tous leurs poids pour chaque mot : ils sont donc plus lents, mais souvent plus intelligents. Tous les modèles ci-dessus peuvent garder le début des chats d'agent sur le SSD ; les dépôts avec un fichier `mtp-` profitent aussi du modèle d'aide MTP.

**Pas la peine :** les modèles denses 70B+ (lents sur un Mac et moins bons que Qwen3.8 27B), les modèles MoE 200B+ compressés en 1 à 3 bits, un 35B en 2-bit au lieu d'un 9B en 8-bit, et les dépôts qui ne sont pas des modèles de chat (noms avec `-Base`, Gemma sans `-it`, modèles d'OCR, de parole ou d'embedding).

## Byteplan et les autres projets

| | Byteplan | [sushi](https://github.com/beamivalice/sushi) | [Strata](https://github.com/Niko1221/Strata) |
|---|---|---|---|
| Tourne sur | Mac | Mac | PC Windows/Linux avec une carte graphique de jeu |
| Qualité du moteur non modifié | oui, seul l'arrondi diffère (comme avec l'assistant propre à llama.cpp) | ses réglages par défaut perdent en qualité (attention et cache KV quantifiés) | non vérifié |
| Modifications de code / nouveau texte (tokens/s, même M3 Max, 2-bit) | **143** / 55 à 77 | 99 / 52 à 75 | (PC uniquement) |
| Lit un prompt (tokens/s) | **647 à 658** | 630 à 649 | (PC uniquement) |
| Un nouveau chat d'agent démarre après | **0.2 s** | 2.7 s | (PC uniquement) |

Sur ce Mac, Byteplan lit les longs prompts 1 à 3 % plus vite que sushi et écrit du nouveau texte 2 à 6 % plus vite ; il modifie le code 44 % plus vite, démarre les chats d'agent 13× plus tôt et garde la qualité de llama.cpp. Détails et sources : [docs/COMPARISON.md](docs/COMPARISON.md).

## Comment ça marche ?

- **Deviner, puis vérifier :** un petit modèle d'aide devine les mots suivants, et Byteplan reprend dans la conversation le texte qui va probablement revenir (les modifications de code se répètent beaucoup). Le grand modèle vérifie toutes les propositions d'un coup et ne garde que ce qu'il aurait écrit de toute façon.
- **Prêt pour les agents :** le long début que les apps d'agent envoient avec chaque chat reste en mémoire et sur le SSD. Un nouveau chat démarre donc tout de suite, même après un redémarrage.
- **Moins d'étapes sur le GPU :** les petites étapes GPU sont regroupées et réécrites pour arrondir exactement comme avant.
- **Réserve d'experts :** le modèle a 512 experts par couche et en utilise 10 par mot. Avec `--spar`, seuls les plus utilisés restent en mémoire. Les autres sont chargés depuis le SSD au moment où il en a besoin.
- **Garde-fou mémoire :** vérifie la mémoire libre avant le démarrage et arrête le modèle avant que votre Mac ne commence à utiliser le swap.

Plus de détails : [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) · les modifications de llama.cpp : [docs/PATCHES.md](docs/PATCHES.md)

## Un problème ?

- **"not enough free RAM"** : fermez d'autres apps (les navigateurs et Docker en utilisent beaucoup) ou utilisez `--spar 410`.
- **"stopped by the memory watchdog"** : même solution. Le garde-fou a arrêté le modèle avant que macOS ne ralentisse.
- **"swap in use"** : macOS garde encore de la mémoire swap d'avant. Redémarrez le Mac.
- **La page affiche "Loading model" un bon moment :** c'est normal au premier démarrage (37 GB à lire). Les démarrages suivants sont plus rapides.
- **`./install.sh` s'est arrêté :** relancez-le, il reprend. Le journal se trouve dans `install.log`.

Toujours bloqué ? Ouvrez une [issue](https://github.com/do-web/byteplan/issues) en indiquant votre Mac, sa mémoire et les dernières lignes du terminal.

## Remerciements et licence

Byteplan s'appuie sur [llama.cpp](https://github.com/ggml-org/llama.cpp) (MIT), le modèle de l'équipe [Qwen](https://huggingface.co/Qwen), les fichiers quantifiés de [ISTA-DASLab](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF), le modèle d'aide MTP de [Joakimpalm-Zen](https://huggingface.co/Joakimpalm-Zen/Qwen3.8-Flash-Next-MTP-GGUF) et la direction de refus de [Cudecnik](https://huggingface.co/Cudecnik/Qwen3.8-Flash-Next-refusal-projection). Byteplan est open source sous [licence MIT](LICENSE). Le modèle a sa propre licence (Qwen Community License 1.0, voir [NOTICE](NOTICE)). Ce dépôt ne contient aucun poids de modèle.

## Soutenir le projet

Byteplan est gratuit et open source. S'il vous est utile, vous pouvez soutenir son développement :

<a href="https://buymeacoffee.com/doweb"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40"></a>
