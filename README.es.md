<h1 align="center">Byteplan</h1>

[English](README.md) · [Deutsch](README.de.md) · **Español** · [Français](README.fr.md) · [Português](README.pt-BR.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

<p align="center"><b>Ejecuta Qwen3.8-Flash-Next, un modelo de IA de 180 mil millones de parámetros, en tu Mac</b><br>
La misma calidad que llama.cpp, 2× más rápido al editar código, los chats con agentes empiezan 18× antes · gratis y de código abierto</p>

Byteplan ejecuta **[Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)** en Macs con Apple Silicon. Chatea, escribe código, lee imágenes y trabaja con tus apps y tus agentes de programación. Nada sale de tu Mac. También puede ejecutar [otros modelos](#otros-modelos) de Hugging Face con un solo comando.

## ¿Qué velocidad tiene?

Medido en un MacBook Pro M3 Max con 64 GB, frente a [llama.cpp](https://github.com/ggml-org/llama.cpp) sin modificar, con el mismo archivo de modelo y el mismo ayudante. Un token es más o menos ¾ de una palabra.

| | llama.cpp | **Byteplan** |
|---|---:|---:|
| Edita código (repite gran parte de tu archivo) | 76 tokens/s | **162 tokens/s** |
| Refactoriza código con un agente | 69 tokens/s | **108 tokens/s** |
| Escribe código nuevo | 74 tokens/s | **80 tokens/s** |
| Escribe texto | 51 tokens/s | **57 tokens/s** |
| Lee un prompt largo | 440 tokens/s | **454 tokens/s** |
| Chat nuevo con un agente: espera hasta la primera palabra | 3.8 s | **0.2 s** |

Desde el 11-10-2026, Byteplan lee los prompts largos un 26 % más rápido con las mismas respuestas, a la par de sushi ([detalles](docs/COMPARISON.md#measured-on-the-same-mac-byteplan-vs-sushi)). Esta tabla se volverá a medir.

**La misma calidad que llama.cpp:** el mismo archivo de modelo, ningún peso cambiado, ningún cálculo omitido. Al comprobar muchas palabras adivinadas a la vez, el modelo redondea un poquito distinto que al escribir palabra por palabra, así que de vez en cuando cambia una palabra. llama.cpp hace lo mismo: su propio ayudante cambia 1 de las 4 respuestas de prueba, y las respuestas de Byteplan coinciden con las de llama.cpp en 3 de 4. Medido sobre 8.000 tokens, ambos se desvían igual de poco ([detalles](docs/HOW_IT_WORKS.md#1-guess-ahead-check-exactly-mtp--n-gram-drafts)). Byteplan es más rápido cuando el texto se repite y cuando empieza un chat. Con texto totalmente nuevo es entre un 8 y un 12 % más rápido. Todas las cifras, el método y cómo medirlo en tu Mac: [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

<p align="center"><a href="https://buymeacoffee.com/doweb"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50"></a><br>
<sub>Byteplan es gratis. Si te ahorra tiempo, un café me ayuda a seguir mejorándolo.</sub></p>

## Qué necesitas

| | |
|---|---|
| **Mac** | Apple Silicon (M1 o posterior). Probado: MacBook Pro M3 Max. Los chips con menos ancho de banda de memoria (Pro, M básico) son más lentos. |
| **Memoria** | **64 GB** (probado). Con 48 GB debería funcionar con `--spar 256` (aún sin probar). Con menos: solo [modelos más pequeños](#otros-modelos). |
| **Disco** | 150 GB libres durante la instalación, unos 70 GB después (+37 GB para `--spar`). |
| **Herramientas** | Herramientas de línea de comandos de Xcode y [Homebrew](https://brew.sh). El instalador te avisa si falta algo. |

### Cuánto texto tiene presente (contexto)

| Contexto | aprox. | Mac con 64 GB | Mac con 48 GB (sin probar) |
|---|---|---|---|
| 64k tokens (por defecto) | 100 páginas | `bin/chat` | `bin/chat --spar 256` |
| 96k tokens | 145 páginas | `bin/chat --long` | `bin/chat --long --spar 256` |
| 256k tokens (el máximo del modelo) | 390 páginas | `bin/chat --max --spar 358` | no cabe |

Más contexto necesita más memoria (~1.4 GB por cada 32k tokens extra). Cuando un chat es más largo que el contexto, se pierde la parte más antigua. La interfaz web puede resumirla por ti (Compact).

## Instalación

### Deja que tu IA lo instale

¿Usas un asistente de programación con IA (Claude Code, Cursor, Codex, ...)? Pégale este texto:

```text
Set up Byteplan on this Mac for me: https://github.com/do-web/byteplan - follow docs/AI_SETUP.md in that repository.
```

### O hazlo tú mismo

Abre la app Terminal y pega estas líneas una a una:

```sh
xcode-select --install                 # una vez; sáltalo si dice "already installed"
brew install git cmake node uv
git clone https://github.com/do-web/byteplan && cd byteplan
./install.sh                           # Mac con 64 GB (48 GB: ./install.sh --spar)
```

El instalador compila Byteplan (unos minutos), descarga el modelo (unos 70 GB) y lo prepara. Si la descarga se corta, vuelve a ejecutar `./install.sh`: sigue donde se quedó.

## Cómo usarlo

```sh
bin/chat
```

Espera hasta que diga que el modelo está cargado (la página del navegador muestra una barra de progreso) y abre **http://127.0.0.1:8080**. Para detenerlo, pulsa `Ctrl-C`.

- **Tus apps:** añade un proveedor "OpenAI-compatible" con la URL base **`http://127.0.0.1:8080/v1`** (cualquier clave de API, cualquier nombre de modelo). Agentes de programación: mira más abajo.
- **Deja que el modelo trabaje con tus archivos:** `bin/chat --agent` da al chat herramientas para leer y escribir archivos y ejecutar comandos. Úsalo solo en tu propio Mac.
- **Imágenes:** adjúntalas en el chat. La primera imagen tarda unos segundos más.
- **¿No tienes suficiente memoria?** `bin/chat --spar 410` (o 358, 256) mantiene menos expertos en memoria. Las respuestas son exactamente las mismas, solo que más lentas ([cifras](docs/HOW_IT_WORKS.md#3-expert-pool-for-smaller-macs---spar-s)). Antes tienes que ejecutar `./install.sh --spar` una vez.
- **Menos rechazos:** `bin/chat --uncensored`, desactivado por defecto ([qué hace](docs/UNCENSORED.md)).

### Agentes de programación (Claude Code, Codex)

Los agentes envían instrucciones largas y listas de herramientas, así que dales más contexto: arranca `bin/chat --long` (96k) o `bin/chat --max --spar 358` (256k). La primera respuesta tarda entre 30 y 70 segundos mientras el modelo lee esas instrucciones (Codex unos 12.000 tokens, Claude Code unos 26.000; más con muchos servidores MCP). Byteplan las guarda en el SSD, así que la siguiente sesión empieza en pocos segundos, también después de un reinicio (Claude Code con 51.000 tokens: unos 90 s la primera vez, 25 s después de un reinicio).

**Claude Code**, en una segunda terminal:

```sh
export ANTHROPIC_BASE_URL=http://127.0.0.1:8080 ANTHROPIC_AUTH_TOKEN=local
export ANTHROPIC_MODEL=qwen3.8-flash-next ANTHROPIC_DEFAULT_HAIKU_MODEL=qwen3.8-flash-next
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=90000    # algo menos que bin/chat --long (98 304): Claude Code cuenta los tokens de otra forma
claude
```

Si dice que la petición supera el tamaño del contexto, es que muchos servidores MCP alargan cada petición: usa `bin/chat --max --spar 358` y `CLAUDE_CODE_MAX_CONTEXT_TOKENS=240000`, o arranca `claude --strict-mcp-config` sin ellos.

**Codex**: añade esto a `~/.codex/config.toml` y luego ejecuta `codex`:

```toml
model = "qwen3.8-flash-next"
model_provider = "byteplan"
model_context_window = 90000

[model_providers.byteplan]
name = "Byteplan"
base_url = "http://127.0.0.1:8080/v1"
wire_api = "responses"
```

## Otros modelos

```sh
bin/run Qwen/Qwen3-8B-GGUF                         # un modelo GGUF ya preparado
bin/run https://huggingface.co/Qwen/Qwen3-8B       # pesos originales: se convierten una vez
bin/run qwen3 8b                                   # ¿no sabes el nombre exacto? muestra coincidencias
```

`bin/run` descarga el modelo, elige el mejor tamaño que quepa en tu memoria (8 bits si cabe: casi sin pérdida de calidad), convierte los pesos originales a GGUF la primera vez y abre la misma interfaz web. Puedes elegir el tamaño tú mismo con `:Q4_K_M` (más rápido) o `:Q8_0` (más preciso). Si solo quieres otros modelos, ejecuta antes `./install.sh --no-model`.

Los otros modelos también reciben las mejoras generales de velocidad (borradores que se adivinan y se comprueban, arranque más rápido para agentes, imágenes solo cuando hacen falta, guardián de memoria). La reserva de expertos y el compilador -O1 están hechos solo para Qwen3.8-Flash-Next.

### ¿Qué modelo para mi Mac?

| Memoria | Modelo | Para empezar | Tamaño | Bueno para |
|---|---|---|---:|---|
| 16 GB | Gemma 4 E4B | `bin/run unsloth/gemma-4-E4B-it-qat-GGUF` | 3.9 GB | chat diario, imágenes |
| 16 GB | Qwen3.5 4B | `bin/run unsloth/Qwen3.5-4B-GGUF` | 4.2 GB | tareas de código pequeñas, herramientas |
| 24 GB | MiMo-V2.6 Distill 9B | `bin/run ggml-org/MiMo-V2.6-Distill-Qwen-9B-GGUF` | 8.9 GB | código y agentes |
| 24 GB | Gemma 4 12B | `bin/run unsloth/gemma-4-12B-it-qat-GGUF` | 6.3 GB | chat, imágenes |
| 32 GB | Qwen3.6 35B-A3B | `bin/run unsloth/Qwen3.6-35B-A3B-GGUF` | 16.8 GB | todoterreno rápido (MoE) |
| 32 GB | Qwen3.8 27B | `bin/run unsloth/Qwen3.8-27B-GGUF` | 16.4 GB | el mejor para código que cabe, más lento |
| 48 GB | Qwen3.8 27B | `bin/run unsloth/Qwen3.8-27B-GGUF` | 27.1 GB | lo mismo, en 8 bits |
| 64 GB | **Qwen3.8-Flash-Next** | `bin/chat` | 37 GB | **el modelo principal: la mejor calidad** |
| 64 GB | Qwen3.6 35B-A3B | `bin/run ggml-org/Qwen3.6-35B-A3B-GGUF` | 34.4 GB | MoE rápido, 8 bits, con ayudante MTP |
| 96–128 GB | Laguna S 2.1 118B-A8B | `bin/run unsloth/Laguna-S-2.1-GGUF` | 68–91 GB | programación con agentes |

Los tamaños son los que elige `bin/run` en ese Mac. Los modelos **MoE** ("A3B" = 3 mil millones de parámetros activos por palabra) son rápidos en un Mac; los modelos **densos** leen todos sus pesos en cada palabra, así que son más lentos, pero a menudo más inteligentes. Todos los modelos de arriba pueden guardar el inicio de los chats con agentes en el SSD; los repos con un archivo `mtp-` también reciben el ayudante MTP.

**No merece la pena:** modelos densos de 70B+ (lentos en un Mac y más débiles que Qwen3.8 27B), modelos MoE de 200B+ comprimidos a entre 1 y 3 bits, un 35B en 2 bits en lugar de un 9B en 8 bits, y repos que no son modelos de chat (nombres con `-Base`, Gemma sin `-it`, modelos de OCR, de voz o de embeddings).

## Byteplan y otros proyectos

| | Byteplan | [sushi](https://github.com/beamivalice/sushi) | [Strata](https://github.com/Niko1221/Strata) |
|---|---|---|---|
| Funciona en | Mac | Mac | PC con Windows/Linux y una tarjeta gráfica para juegos |
| Calidad del motor sin modificar | sí, solo cambia el redondeo (como con el ayudante propio de llama.cpp) | sus ajustes por defecto pierden calidad (atención y caché KV cuantizadas) | sin comprobar |
| Edición de código / texto nuevo (tokens/s, mismo M3 Max, 2 bits) | **143** / 55 a 77 | 99 / 52 a 75 | (solo PC) |
| Lee un prompt (tokens/s) | **647 a 658** | 630 a 649 | (solo PC) |
| Un chat nuevo con un agente empieza tras | **0.2 s** | 2.7 s | (solo PC) |

En este Mac, Byteplan lee los prompts largos entre un 1 y un 3 % más rápido que sushi y escribe texto nuevo entre un 2 y un 6 % más rápido; edita código un 44 % más rápido, inicia los chats con agentes 13× antes y mantiene la calidad de llama.cpp. Detalles y fuentes: [docs/COMPARISON.md](docs/COMPARISON.md).

## ¿Cómo funciona?

- **Adivinar y luego comprobar:** un pequeño ayudante adivina las siguientes palabras, y Byteplan copia texto probable de la conversación (al editar código se repite mucho). El modelo grande comprueba todas las suposiciones a la vez y solo se queda con lo que habría escrito de todos modos.
- **Preparado para agentes:** el largo texto inicial que las apps de agentes envían en cada chat se guarda en memoria y en el SSD. Así un chat nuevo empieza al instante, también después de un reinicio.
- **Menos pasos en la GPU:** los pasos pequeños de la GPU se unen y se reescriben para que redondeen exactamente igual que antes.
- **Reserva de expertos:** el modelo tiene 512 expertos por capa y usa 10 por palabra. Con `--spar`, solo los más usados se quedan en memoria y el resto se carga desde el SSD justo cuando hace falta.
- **Guardián de memoria:** comprueba la memoria libre antes de arrancar y detiene el modelo antes de que tu Mac empiece a usar el disco como memoria (swap).

Más: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) · los cambios en llama.cpp: [docs/PATCHES.md](docs/PATCHES.md)

## ¿Algo no funciona?

- **"not enough free RAM"**: cierra otras apps (los navegadores y Docker usan mucha) o usa `--spar 410`.
- **"stopped by the memory watchdog"**: la misma solución. El guardián detuvo el modelo antes de que macOS se volviera lento.
- **"swap in use"**: macOS todavía tiene memoria en el disco (swap) de antes. Reinicia tu Mac.
- **La página dice "Loading model" durante un rato:** es normal en el primer arranque (hay que leer 37 GB). Los siguientes arranques son más rápidos.
- **`./install.sh` se detuvo:** vuelve a ejecutarlo; sigue donde se quedó. El registro está en `install.log`.

¿Sigues sin poder avanzar? Abre un [issue](https://github.com/do-web/byteplan/issues) con tu modelo de Mac, la memoria y las últimas líneas de la terminal.

## Créditos y licencia

Byteplan se apoya en [llama.cpp](https://github.com/ggml-org/llama.cpp) (MIT), el modelo del equipo de [Qwen](https://huggingface.co/Qwen), los archivos cuantizados de [ISTA-DASLab](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF), el ayudante MTP de [Joakimpalm-Zen](https://huggingface.co/Joakimpalm-Zen/Qwen3.8-Flash-Next-MTP-GGUF) y la dirección de rechazo de [Cudecnik](https://huggingface.co/Cudecnik/Qwen3.8-Flash-Next-refusal-projection). Byteplan es de código abierto bajo la [Licencia MIT](LICENSE). El modelo tiene su propia licencia (Qwen Community License 1.0, ver [NOTICE](NOTICE)). Este repositorio no contiene pesos del modelo.

## Apoyo

Byteplan es gratis y de código abierto. Si te resulta útil, puedes apoyar su desarrollo:

<a href="https://buymeacoffee.com/doweb"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40"></a>
