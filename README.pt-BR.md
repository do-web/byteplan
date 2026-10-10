<h1 align="center">Byteplan</h1>

[English](README.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · **Português** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

<p align="center"><b>Rode o Qwen3.8-Flash-Next, um modelo de IA com 180 bilhões de parâmetros, no seu Mac</b><br>
A mesma qualidade do llama.cpp, 2× mais rápido ao editar código, chats com agentes começam 18× mais rápido · grátis e de código aberto</p>

O Byteplan roda o **[Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)** em um Mac com Apple Silicon. Ele conversa, escreve código, lê imagens e trabalha com seus apps e agentes de programação. Nada sai do seu Mac. Ele também roda [outros modelos](#outros-modelos) do Hugging Face com um único comando.

## Quão rápido ele é?

Medido em um MacBook Pro M3 Max com 64 GB, comparado ao [llama.cpp](https://github.com/ggml-org/llama.cpp) puro, com o mesmo arquivo de modelo e o mesmo modelo auxiliar. Um token é mais ou menos ¾ de uma palavra.

| | llama.cpp | **Byteplan** |
|---|---:|---:|
| Edita código (repete boa parte do seu arquivo) | 76 tokens/s | **162 tokens/s** |
| Refatora código em um agente | 69 tokens/s | **108 tokens/s** |
| Escreve código novo | 74 tokens/s | **80 tokens/s** |
| Escreve texto | 51 tokens/s | **57 tokens/s** |
| Lê um prompt longo | 440 tokens/s | **454 tokens/s** |
| Novo chat de agente: espera até a primeira palavra | 3.8 s | **0.2 s** |

Desde 11/10/2026 o Byteplan lê prompts longos 26 % mais rápido, com as mesmas respostas, empatado com o sushi ([detalhes](docs/COMPARISON.md#measured-on-the-same-mac-byteplan-vs-sushi)). Esta tabela vai ser medida de novo.

**A mesma qualidade do llama.cpp:** o mesmo arquivo de modelo, nenhum peso alterado, nenhum cálculo pulado. Ao conferir várias palavras adivinhadas de uma vez, o modelo arredonda um pouquinho diferente de quando escreve palavra por palavra, então de vez em quando uma palavra muda. O llama.cpp faz o mesmo: o próprio ajudante dele muda 1 das 4 respostas de teste, e as respostas do Byteplan batem com as do llama.cpp em 3 de 4. Medido em 8.000 tokens, os dois se desviam igualmente pouco ([detalhes](docs/HOW_IT_WORKS.md#1-guess-ahead-check-exactly-mtp--n-gram-drafts)). O Byteplan é mais rápido quando o texto se repete e quando um chat começa. Para texto totalmente novo, ele é 8 a 12 % mais rápido. Todos os números, o método e como medir no seu Mac: [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

<p align="center"><a href="https://buymeacoffee.com/doweb"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50"></a><br>
<sub>O Byteplan é gratuito. Se ele economiza seu tempo, um café me ajuda a continuar melhorando o projeto.</sub></p>

## Do que você precisa

| | |
|---|---|
| **Mac** | Apple Silicon (M1 ou mais novo). Testado: MacBook Pro M3 Max. Chips com menos largura de banda de memória (Pro, M básico) são mais lentos. |
| **Memória** | **64 GB** (testado). 48 GB deve funcionar com `--spar 256` (ainda não testado). Menos que isso: só [modelos menores](#outros-modelos). |
| **Disco** | 150 GB livres durante a instalação, cerca de 70 GB depois (+37 GB para `--spar`). |
| **Ferramentas** | Ferramentas de linha de comando do Xcode e [Homebrew](https://brew.sh). O instalador avisa se faltar algo. |

### Quanto texto ele consegue ter em mente (contexto)

| Contexto | cerca de | Mac com 64 GB | Mac com 48 GB (não testado) |
|---|---|---|---|
| 64k tokens (padrão) | 100 páginas | `bin/chat` | `bin/chat --spar 256` |
| 96k tokens | 145 páginas | `bin/chat --long` | `bin/chat --long --spar 256` |
| 256k tokens (o máximo do modelo) | 390 páginas | `bin/chat --max --spar 358` | não cabe |

Mais contexto precisa de mais memória (~1.4 GB a cada 32k tokens extras). Quando um chat fica maior que o contexto, a parte mais antiga é descartada. A interface web pode resumir essa parte para você (Compact).

## Instalação

### Deixe sua IA configurar tudo

Você usa um assistente de programação com IA (Claude Code, Cursor, Codex, ...)? Cole isto nele:

```text
Set up Byteplan on this Mac for me: https://github.com/do-web/byteplan - follow docs/AI_SETUP.md in that repository.
```

### Ou faça você mesmo

Abra o app Terminal e cole estas linhas, uma de cada vez:

```sh
xcode-select --install                 # só uma vez; pule se aparecer "already installed"
brew install git cmake node uv
git clone https://github.com/do-web/byteplan && cd byteplan
./install.sh                           # Mac com 64 GB (48 GB: ./install.sh --spar)
```

O instalador compila o Byteplan (alguns minutos), baixa o modelo (cerca de 70 GB) e deixa tudo pronto. Se o download parar, rode `./install.sh` de novo: ele continua de onde parou.

## Como usar

```sh
bin/chat
```

Espere até aparecer que o modelo foi carregado (a página no navegador mostra uma barra de progresso). Depois abra **http://127.0.0.1:8080**. Para parar, use `Ctrl-C`.

- **Seus apps:** adicione um provedor "compatível com OpenAI" (OpenAI-compatible) com a URL base **`http://127.0.0.1:8080/v1`** (qualquer chave de API, qualquer nome de modelo). Agentes de programação: veja abaixo.
- **Deixe o modelo trabalhar nos seus arquivos:** `bin/chat --agent` dá ao chat ferramentas para ler e escrever arquivos e rodar comandos. Use só no seu próprio Mac.
- **Imagens:** anexe no chat. A primeira imagem leva alguns segundos a mais.
- **Falta memória?** `bin/chat --spar 410` (ou 358, 256) mantém menos especialistas na memória. As respostas continuam exatamente iguais, só ficam mais lentas ([números](docs/HOW_IT_WORKS.md#3-expert-pool-for-smaller-macs---spar-s)). Precisa rodar `./install.sh --spar` uma vez antes.
- **Menos recusas:** `bin/chat --uncensored`, desligado por padrão ([o que ele faz](docs/UNCENSORED.md)).

### Agentes de programação (Claude Code, Codex)

Os agentes enviam instruções longas e listas de ferramentas, então dê mais contexto a eles: rode `bin/chat --long` (96k) ou `bin/chat --max --spar 358` (256k). A primeira resposta leva de 30 a 70 segundos, enquanto o modelo lê essas instruções (no Codex, cerca de 12.000 tokens; no Claude Code, cerca de 26.000; mais com muitos servidores MCP). O Byteplan guarda essas instruções no SSD, então a próxima sessão começa em poucos segundos, mesmo depois de reiniciar (Claude Code com 51.000 tokens: cerca de 90 s na primeira vez, 25 s depois de reiniciar).

**Claude Code**, em um segundo terminal:

```sh
export ANTHROPIC_BASE_URL=http://127.0.0.1:8080 ANTHROPIC_AUTH_TOKEN=local
export ANTHROPIC_MODEL=qwen3.8-flash-next ANTHROPIC_DEFAULT_HAIKU_MODEL=qwen3.8-flash-next
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=90000    # um pouco abaixo de bin/chat --long (98.304): o Claude Code conta tokens de outro jeito
claude
```

Se aparecer que a requisição é maior que o tamanho do contexto, é porque muitos servidores MCP estão deixando cada requisição mais longa: use `bin/chat --max --spar 358` e `CLAUDE_CODE_MAX_CONTEXT_TOKENS=240000`, ou inicie `claude --strict-mcp-config` sem eles.

**Codex**: adicione isto ao `~/.codex/config.toml` e depois rode `codex`:

```toml
model = "qwen3.8-flash-next"
model_provider = "byteplan"
model_context_window = 90000

[model_providers.byteplan]
name = "Byteplan"
base_url = "http://127.0.0.1:8080/v1"
wire_api = "responses"
```

## Outros modelos

```sh
bin/run Qwen/Qwen3-8B-GGUF                         # um modelo GGUF pronto
bin/run https://huggingface.co/Qwen/Qwen3-8B       # pesos originais: convertidos uma vez
bin/run qwen3 8b                                   # não sabe o nome exato? mostra as opções
```

O `bin/run` baixa o modelo, escolhe o melhor tamanho que cabe na sua memória (8 bits se couber: quase sem perda de qualidade), converte os pesos originais para GGUF na primeira vez e abre a mesma interface web. Para escolher o tamanho você mesmo, use `:Q4_K_M` (mais rápido) ou `:Q8_0` (mais preciso). Se você só quer outros modelos, rode antes `./install.sh --no-model`.

Outros modelos também ganham as acelerações gerais (palpites conferidos pelo modelo, início mais rápido para agentes, imagens só quando precisa, proteção de memória). O pool de especialistas e o compilador -O1 foram feitos só para o Qwen3.8-Flash-Next.

### Qual modelo para o meu Mac?

| Memória | Modelo | Comece com | Tamanho | Bom para |
|---|---|---|---:|---|
| 16 GB | Gemma 4 E4B | `bin/run unsloth/gemma-4-E4B-it-qat-GGUF` | 3.9 GB | chat do dia a dia, imagens |
| 16 GB | Qwen3.5 4B | `bin/run unsloth/Qwen3.5-4B-GGUF` | 4.2 GB | pequenas tarefas de código, ferramentas |
| 24 GB | MiMo-V2.6 Distill 9B | `bin/run ggml-org/MiMo-V2.6-Distill-Qwen-9B-GGUF` | 8.9 GB | código e agentes |
| 24 GB | Gemma 4 12B | `bin/run unsloth/gemma-4-12B-it-qat-GGUF` | 6.3 GB | chat, imagens |
| 32 GB | Qwen3.6 35B-A3B | `bin/run unsloth/Qwen3.6-35B-A3B-GGUF` | 16.8 GB | rápido e versátil (MoE) |
| 32 GB | Qwen3.8 27B | `bin/run unsloth/Qwen3.8-27B-GGUF` | 16.4 GB | o melhor em código que cabe, mais lento |
| 48 GB | Qwen3.8 27B | `bin/run unsloth/Qwen3.8-27B-GGUF` | 27.1 GB | o mesmo, em 8 bits |
| 64 GB | **Qwen3.8-Flash-Next** | `bin/chat` | 37 GB | **o modelo principal: a melhor qualidade** |
| 64 GB | Qwen3.6 35B-A3B | `bin/run ggml-org/Qwen3.6-35B-A3B-GGUF` | 34.4 GB | MoE rápido, 8 bits, com o auxiliar MTP |
| 96–128 GB | Laguna S 2.1 118B-A8B | `bin/run unsloth/Laguna-S-2.1-GGUF` | 68–91 GB | programação com agentes |

Os tamanhos são o que o `bin/run` escolhe nesse Mac. Modelos **MoE** ("A3B" = 3 bilhões de parâmetros ativos por palavra) são rápidos em um Mac; modelos **densos** leem todos os seus pesos a cada palavra, então são mais lentos, mas muitas vezes mais inteligentes. Todos os modelos acima podem guardar o início dos chats de agentes no SSD; repositórios com um arquivo `mtp-` também ganham o auxiliar MTP.

**Não vale a pena:** modelos densos 70B+ (lentos em um Mac e mais fracos que o Qwen3.8 27B), modelos MoE 200B+ espremidos em 1 a 3 bits, um 35B em 2 bits em vez de um 9B em 8 bits, e repositórios que não são modelos de chat (nomes com `-Base`, Gemma sem `-it`, modelos de OCR, de fala ou de embedding).

## O Byteplan e outros projetos

| | Byteplan | [sushi](https://github.com/beamivalice/sushi) | [Strata](https://github.com/Niko1221/Strata) |
|---|---|---|---|
| Roda em | Mac | Mac | PC com Windows/Linux e placa de vídeo gamer |
| Qualidade do motor sem modificações | sim, só o arredondamento muda (como com o ajudante do próprio llama.cpp) | as configurações padrão dele perdem qualidade (atenção e cache KV quantizados) | não conferido |
| Edições de código / texto novo (tokens/s, mesmo M3 Max, 2 bits) | **143** / 55 a 77 | 99 / 52 a 75 | (só PC) |
| Lê um prompt (tokens/s) | **647 a 658** | 630 a 649 | (só PC) |
| Novo chat de agente começa depois de | **0.2 s** | 2.7 s | (só PC) |

Neste Mac, o Byteplan lê prompts longos 1 a 3 % mais rápido que o sushi e escreve texto novo 2 a 6 % mais rápido; edita código 44 % mais rápido, inicia chats com agentes 13× antes e mantém a qualidade do llama.cpp. Detalhes e fontes: [docs/COMPARISON.md](docs/COMPARISON.md).

## Como funciona?

- **Adivinhar e conferir:** um pequeno modelo auxiliar adivinha as próximas palavras, e o Byteplan copia da conversa o texto provável (edições de código repetem muita coisa). O modelo grande confere todos os palpites de uma vez e só mantém o que ele mesmo teria escrito.
- **Pronto para agentes:** o longo trecho inicial que os apps de agentes enviam em cada chat fica guardado na memória e no SSD. Assim, um novo chat começa na hora, mesmo depois de reiniciar.
- **Menos passos na GPU:** pequenos passos na GPU são juntados e reescritos para arredondar exatamente como antes.
- **Pool de especialistas:** o modelo tem 512 especialistas (experts) por camada e usa 10 por palavra. Com `--spar`, só os mais usados ficam na memória. O resto é carregado do SSD no momento em que faz falta.
- **Proteção de memória:** confere a memória livre antes de começar e para o modelo antes que o seu Mac comece a usar swap.

Mais: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) · as mudanças no llama.cpp: [docs/PATCHES.md](docs/PATCHES.md)

## Deu algo errado?

- **"not enough free RAM"**: feche outros apps (navegadores e Docker usam muita memória) ou use `--spar 410`.
- **"stopped by the memory watchdog"**: mesma solução. A proteção parou o modelo antes que o macOS ficasse lento.
- **"swap in use"**: o macOS ainda guarda memória de swap de antes. Reinicie o Mac.
- **A página mostra "Loading model" por um tempo:** é normal na primeira vez (37 GB para ler). As próximas vezes são mais rápidas.
- **O `./install.sh` parou:** rode de novo; ele continua. O log fica em `install.log`.

Ainda com problemas? Abra uma [issue](https://github.com/do-web/byteplan/issues) com o modelo do seu Mac, a memória e as últimas linhas do terminal.

## Créditos e licença

O Byteplan se apoia no [llama.cpp](https://github.com/ggml-org/llama.cpp) (MIT), no modelo da equipe [Qwen](https://huggingface.co/Qwen), nos arquivos quantizados da [ISTA-DASLab](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF), no modelo auxiliar MTP de [Joakimpalm-Zen](https://huggingface.co/Joakimpalm-Zen/Qwen3.8-Flash-Next-MTP-GGUF) e na direção de recusa de [Cudecnik](https://huggingface.co/Cudecnik/Qwen3.8-Flash-Next-refusal-projection). O Byteplan é de código aberto, sob a [Licença MIT](LICENSE). O modelo tem sua própria licença (Qwen Community License 1.0, veja [NOTICE](NOTICE)). Este repositório não contém pesos de modelo.

## Apoio

O Byteplan é gratuito e de código aberto. Se ele for útil para você, você pode apoiar o desenvolvimento:

<a href="https://buymeacoffee.com/doweb"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40"></a>
