#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "numba"]
# ///
"""Expert-pool profile for llama_spar from router traces (`byteplan experts`): per layer the LRU miss curve and the
experts ranked by use. llama_spar reads it from `<experts.bin>.profile` to give layers with more misses more slots
(same total RAM) and to preload the most used experts instead of 0..S-1. Only residency changes, outputs stay
bit-identical.

Layout (little-endian): "BPPROF1\\0", u32 version=1, u32 n_layer, u32 n_expert, u32 n_tokens,
  n_layer x { f32 miss[n_expert + 1] (misses per token with C slots, C = 0..n_expert), u16 rank[n_expert] }.
Layers without trace data (the last layer of prefill traces) get the mean curve and rank 0..n_expert-1.
Usage: uv run tools/experts/profile.py --out <experts.bin>.profile <trace-dir> [<trace-dir> ...]
"""
import argparse
import struct
from pathlib import Path

import numba as nb
import numpy as np

K = 10
UNKNOWN = 0xFFFF
WARM = 2048  # tokens per document before misses count (cold start)


@nb.njit(cache=True)
def add_doc(tr, n_expert, hist, freq):
    """LRU stack-distance histogram (distance n_expert = cold) and use counts per layer."""
    n_tok, n_layer, k = tr.shape
    for l in range(n_layer):
        if tr[0, l, 0] == UNKNOWN:
            continue
        order = np.arange(n_expert)
        pos = np.arange(n_expert)
        seen = np.zeros(n_expert, np.bool_)
        for t in range(n_tok):
            for j in range(k):
                e = tr[t, l, j]
                freq[l, e] += 1
                d = pos[e] if seen[e] else n_expert
                if t >= WARM:
                    hist[l, d] += 1
                seen[e] = True
                for q in range(pos[e], 0, -1):
                    order[q] = order[q - 1]
                    pos[order[q]] = q
                order[0] = e
                pos[e] = 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--layers", type=int, default=48)
    ap.add_argument("--experts", type=int, default=512)
    a = ap.parse_args()

    files = sorted(p for d in a.dirs for p in d.glob("*.experts.u16"))
    if not files:
        raise SystemExit("no *.experts.u16 found")
    hist = np.zeros((a.layers, a.experts + 1), np.int64)
    freq = np.zeros((a.layers, a.experts), np.int64)
    n_tok = 0
    for f in files:
        tr = np.fromfile(f, dtype="<u2").reshape(-1, a.layers, K).astype(np.int64)
        add_doc(np.ascontiguousarray(tr), a.experts, hist, freq)
        n_tok += max(0, tr.shape[0] - WARM)
        print(f"{f.name}: {tr.shape[0]} tokens")
    known = hist.sum(axis=1) > 0
    miss = np.cumsum(hist[:, ::-1], axis=1)[:, ::-1] / n_tok  # miss[l, C]
    miss[~known] = miss[known].mean(axis=0)
    rank = np.argsort(-freq, axis=1, kind="stable").astype("<u2")
    rank[~known] = np.arange(a.experts, dtype="<u2")

    with open(a.out, "xb") as f:
        f.write(b"BPPROF1\0" + struct.pack("<IIII", 1, a.layers, a.experts, n_tok))
        for l in range(a.layers):
            f.write(miss[l].astype("<f4").tobytes() + rank[l].tobytes())
    print(f"{a.out}: {len(files)} documents, {n_tok} tokens, {known.sum()} layers with data")


if __name__ == "__main__":
    main()
