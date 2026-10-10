#!/usr/bin/env bash
# Byteplan installer: checks the Mac, builds the patched llama.cpp, downloads and prepares Qwen3.8-Flash-Next.
#
#   ./install.sh                 everything (~72 GB download, ~70 GB on disk afterwards, ~115 GB while compiling)
#   ./install.sh --spar          also the expert pool for bin/chat --spar (+37 GB disk; automatic below 64 GB RAM)
#   ./install.sh --uncensored    also the refusal-removal direction for bin/chat --uncensored (0.5 MB)
#   ./install.sh --no-model      only build (enough for bin/run with other models)
#
# Safe to run again: finished steps are skipped. Models go to $BYTEPLAN_MODELS (default ~/byteplan-models).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
D="${BYTEPLAN_MODELS:-$HOME/byteplan-models}"
LLAMA_REPO=https://github.com/ggml-org/llama.cpp
LLAMA_SHA=18b5f8b1862ebfe0f1c33d2355b81a54d2fec867
SRC="$ROOT/vendor/llama.cpp"
ISTA="$D/ista/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf"
O1="$D/ista-o1/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-dense-q8_0-router-q8_0-00001-of-00002.gguf"
SP="$D/ista-o1-spar/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-dense-q8_0-router-q8_0-spar"
MTP="$D/mtp/Qwen3.8-Flash-Next-MTP"

SPAR=0 UNCENSORED=0 MODEL=1
for a in "$@"; do
  case "$a" in
    --spar) SPAR=1 ;;
    --uncensored) UNCENSORED=1 ;;
    --no-model) MODEL=0 ;;
    -h|--help) sed -n '2,9p' "$0" | cut -c3-; exit 0 ;;
    *) echo "install: unknown option $a (see ./install.sh --help)" >&2; exit 2 ;;
  esac
done

step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die() { printf '\ninstall: %s\n' "$*" >&2; exit 1; }
LOG="$ROOT/install.log"
: > "$LOG"
# long tool output goes to install.log; on failure show its end
quiet() { "$@" >>"$LOG" 2>&1 || { tail -25 "$LOG" >&2; die "step failed: $1 (full log: install.log)"; }; }

step "Checking this Mac"
[ "$(uname -s)/$(uname -m)" = Darwin/arm64 ] || die "Byteplan needs a Mac with Apple Silicon (M1 or newer)."
RAM_GB=$(( $(sysctl -n hw.memsize) / 1073741824 ))
echo "memory: $RAM_GB GB"
if [ "$MODEL" = 1 ]; then
  [ "$RAM_GB" -ge 48 ] || die "Qwen3.8-Flash-Next needs at least 48 GB memory (this Mac has $RAM_GB GB). Smaller models: ./install.sh --no-model, then bin/run."
  if [ "$RAM_GB" -lt 64 ] && [ "$SPAR" = 0 ]; then echo "less than 64 GB: installing the expert pool too (--spar)"; SPAR=1; fi
  # peak while compiling ~115 GB (download + -O1 copy); afterwards ~70 GB, the expert pool adds 37 GB after cleanup
  NEED=115
  [ -f "$O1" ] && NEED=$(( 70 + SPAR * 37 ))
  mkdir -p "$D"
  # only the Qwen files count as already there (bin/run keeps other models in the same folder)
  HAVE=0
  for d in ista ista-o1 ista-o1-spar mtp; do [ -d "$D/$d" ] && HAVE=$(( HAVE + $(du -sg "$D/$d" | cut -f1) )); done
  FREE=$(df -g "$D" | awk 'NR==2{print $4}')
  echo "disk: needs ~$NEED GB in $D (has $HAVE GB already), $FREE GB free"
  [ $(( FREE + HAVE - NEED )) -ge 30 ] || die "not enough free disk space: free up ~$(( NEED - HAVE + 30 - FREE )) GB (30 GB stay free as a reserve)."
fi

step "Checking tools"
xcode-select -p >/dev/null 2>&1 || die "the Xcode command line tools are missing. Run: xcode-select --install  (then ./install.sh again)"
missing=()
for t in cmake uv node; do command -v "$t" >/dev/null || missing+=("$t"); done
[ -d /opt/homebrew/opt/openssl@3 ] || [ -d /usr/local/opt/openssl@3 ] || missing+=(openssl@3)
if [ ${#missing[@]} -gt 0 ]; then
  command -v brew >/dev/null || die "missing: ${missing[*]}. Install Homebrew from https://brew.sh, then ./install.sh again."
  echo "installing with Homebrew: ${missing[*]}"
  brew install "${missing[@]}"
fi

step "Getting llama.cpp ${LLAMA_SHA:0:9} and applying the Byteplan patches"
PATCHES=()
while read -r p; do PATCHES+=("$ROOT/patches/$p"); done < "$ROOT/patches/series"
if [ ! -d "$SRC/.git" ]; then
  rm -rf "$SRC.tmp"
  git init -q "$SRC.tmp"
  git -C "$SRC.tmp" fetch -q --depth 1 "$LLAMA_REPO" "$LLAMA_SHA"
  git -C "$SRC.tmp" checkout -q FETCH_HEAD
  git -C "$SRC.tmp" -c user.name=byteplan -c user.email=byteplan@localhost am -q "${PATCHES[@]}"
  mv "$SRC.tmp" "$SRC"
fi
[ "$(git -C "$SRC" rev-list --count "$LLAMA_SHA"..HEAD)" = "${#PATCHES[@]}" ] \
  || die "vendor/llama.cpp does not match patches/ (changed by hand?). Delete vendor/llama.cpp and run ./install.sh again."

step "Building (about 5-10 minutes the first time)"
OPENSSL="$(brew --prefix openssl@3 2>/dev/null || true)"
quiet cmake -S "$SRC" -B "$ROOT/build" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
  -DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF \
  -DLLAMA_BUILD_UI=ON -DLLAMA_USE_PREBUILT_UI=OFF ${OPENSSL:+-DOPENSSL_ROOT_DIR="$OPENSSL"}
quiet cmake --build "$ROOT/build" -j --target llama-server llama-quantize llama-app
[ -f "$ROOT/build/tools/ui/dist/index.html" ] || die "the web UI did not build (needs node), see install.log"
quiet uv sync --project "$ROOT/tools/compiler"

if [ "$MODEL" = 0 ]; then
  step "Done. Start any model with: bin/run <model>   (e.g. bin/run unsloth/Qwen3-8B-GGUF)"
  exit 0
fi

step "Downloading Qwen3.8-Flash-Next (resumes if interrupted)"
WANT=(qwen-meta)
[ -f "$MTP-Q4_K_M.gguf" ] || WANT+=(mtp)
if [ -f "$O1" ]; then WANT+=('ista/mmproj-*'); else WANT+=(ista); fi
[ "$UNCENSORED" = 1 ] && WANT+=(cudecnik)
"$ROOT/tools/fetch_models.sh" "${WANT[@]}"

PY="$ROOT/tools/compiler/.venv/bin/python"
if [ ! -f "$O1" ]; then
  step "Compiling -O1 (hyper-connections and router to 8 bit, ~10 minutes)"
  "$PY" "$ROOT/tools/compiler/rewrite.py" --in "$ISTA" --out "$D/ista-o1" --router q8_0
  rm -f "$D"/ista/Q2_0/*.gguf  # -O1 replaces shard 1; shard 2 lives on as a hard link in ista-o1
fi

if [ ! -f "$MTP-Q4_K_M.gguf" ]; then
  step "Preparing the MTP draft head (4 bit)"
  quiet "$ROOT/build/bin/llama-quantize" --allow-requantize "$MTP-Q8_0.gguf" "$MTP-Q4_K_M.gguf" Q4_K_M
  chmod a-w "$MTP-Q4_K_M.gguf"
  rm -f "$MTP-Q8_0.gguf"
fi

if [ ! -f "$MTP-Q4_K_M-head2.gguf" ]; then
  step "Making the 2-bit vocabulary head for faster drafts (~10 s)"
  # only output.weight changes (Q6_K -> Q2_K); every other tensor keeps its type and is copied byte for byte
  quiet "$ROOT/build/bin/llama-quantize" --allow-requantize --output-tensor-type q2_K "$MTP-Q4_K_M.gguf" "$MTP-head2.part" Q4_K_M
  mv "$MTP-head2.part" "$MTP-Q4_K_M-head2.gguf"
  chmod a-w "$MTP-Q4_K_M-head2.gguf"
fi

if [ "$SPAR" = 1 ]; then
  if [ ! -f "$SP.experts.bin" ]; then
    step "Building the expert pool for --spar (~2 minutes)"
    "$PY" "$ROOT/tools/compiler/spar_pack.py" --in "$O1" --out "$D/ista-o1-spar"
  fi
  [ -f "$SP.experts.bin.profile" ] || cp "$ROOT/data/qwen3.8-flash-next.spar-profile" "$SP.experts.bin.profile"
fi

START="bin/chat"
[ "$RAM_GB" -lt 64 ] && START="bin/chat --spar 256"
step "Done. Start with: $START   then open http://127.0.0.1:8080"
