#!/usr/bin/env bash
# Download pinned model files from models.lock, verify SHA256, make read-only.
# Usage: tools/fetch_models.sh [filter ...]   filter = a dest folder ("mtp") or a glob on dest/path ('ista/mmproj-*');
#        no filter = everything
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODELS="${BYTEPLAN_MODELS:-$HOME/byteplan-models}"
LOCK="$ROOT/models.lock"
MIN_FREE_GIB=30
# plain HTTP resumes .incomplete files; the Xet transfer stalled here for hours on a slow line
export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-1}"

mkdir -p "$MODELS"
touch "$MODELS/.metadata_never_index"

HF=(hf)
command -v hf >/dev/null || HF=(uvx --from huggingface_hub hf)
wanted() { # dest path: no filter, or a filter equal to dest or matching dest/path as a glob
  [ ${#FILTERS[@]} -eq 0 ] && return 0
  local f
  # shellcheck disable=SC2053  # the filter is a glob on purpose
  for f in "${FILTERS[@]}"; do [[ "$1" == "$f" || "$1/$2" == $f ]] && return 0; done
  return 1
}
FILTERS=("$@")

# one pass over models.lock: the selected lines and the bytes still to download
ROWS=() need_bytes=0
while IFS=$'\t' read -r repo rev path sha size dest; do
  [[ "$repo" == \#* || -z "$repo" ]] && continue
  wanted "$dest" "$path" || continue
  ROWS+=("$repo"$'\t'"$rev"$'\t'"$path"$'\t'"$sha"$'\t'"$dest")
  [[ -f "$MODELS/$dest/$path" ]] || need_bytes=$((need_bytes + size))
done < "$LOCK"
need_gib=$(( need_bytes / 1024 / 1024 / 1024 + 1 ))
free_gib=$(df -g "$MODELS" | awk 'NR==2{print $4}')
if (( free_gib - need_gib < MIN_FREE_GIB )); then
  echo "ABORT: need ${need_gib} GiB, free ${free_gib} GiB, must keep ${MIN_FREE_GIB} GiB free" >&2
  exit 1
fi

for row in ${ROWS[@]+"${ROWS[@]}"}; do
  IFS=$'\t' read -r repo rev path sha dest <<< "$row"
  target="$MODELS/$dest/$path"
  if [[ ! -f "$target" ]]; then
    echo ">> $repo@${rev:0:8} $path"
    # the line drops connections now and then; hf resumes the .incomplete file, so just retry
    tries=0
    until "${HF[@]}" download "$repo" "$path" --revision "$rev" --local-dir "$MODELS/$dest" >/dev/null; do
      tries=$((tries + 1))
      (( tries < 100 )) || { echo "giving up after $tries attempts: $path" >&2; exit 3; }
      echo "   retry $tries in 15 s" >&2
      sleep 15
    done
  fi
  # read-only = verified on an earlier run; openssl hashes ~5x faster than shasum
  if [[ "$sha" != "-" && -w "$target" ]]; then
    actual=$(openssl dgst -sha256 -r "$target" | cut -d' ' -f1)
    [[ "$actual" == "$sha" ]] || { echo "SHA256 MISMATCH: $target" >&2; exit 2; }
  fi
  chmod a-w "$target"
  echo "ok  $dest/$path"
done
