#!/usr/bin/env python3
"""Expert locality from router traces (`byteplan experts`): how much RAM an expert cache needs for which hit rate.

Each trace file holds uint16 expert ids as [token][layer][k]; 0xFFFF = unknown (last layer in prefill traces).
Every document starts with a cold cache. Per layer, an LRU cache of C experts hits when the expert was among
the C most recently used ones; that is the stack (reuse) distance, so one pass yields the whole curve.
Usage: simulate.py <trace-dir> [<trace-dir> ...] [--ssd-gbps 6] [--tps 50]
"""
import argparse
from pathlib import Path

import numpy as np

N_EXPERT = 512
UNKNOWN = 0xFFFF
# ffn_gate/up/down_exps of ista-o1 (Q2_0): 3 x 235.93 MB per layer over 512 experts
EXPERT_MB = 3 * 235.93 / N_EXPERT


def load(path: Path, n_layer: int, k: int) -> np.ndarray:
    ids = np.fromfile(path, dtype="<u2").reshape(-1, n_layer, k)
    known = ids[0, :, 0] != UNKNOWN
    return ids[:, known, :]


def stack_distances(trace: np.ndarray) -> np.ndarray:
    """Per access: number of distinct experts of that layer used since its last use (N_EXPERT = never seen)."""
    n_tok, n_layer, _ = trace.shape
    last = np.full((n_layer, N_EXPERT), -1, dtype=np.int64)
    out = np.empty(trace.shape, dtype=np.int32)
    rows = np.arange(n_layer)[:, None]
    for t in range(n_tok):
        sel = trace[t]  # [layer, k]
        seen = last[rows, sel]  # last use of the selected experts
        # experts used more recently than e = those with last > last[e]; unseen -> cold miss
        dist = (last[:, None, :] > seen[:, :, None]).sum(axis=2)
        out[t] = np.where(seen < 0, N_EXPERT, dist)
        last[rows, sel] = t
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+", type=Path)
    ap.add_argument("--layers", type=int, default=48)
    ap.add_argument("-k", type=int, default=10)
    ap.add_argument("--ssd-gbps", type=float, default=6.0, help="sustained SSD read for expert misses")
    ap.add_argument("--tps", type=float, default=50.0, help="current decode speed, sets the time budget per token")
    a = ap.parse_args()

    files = sorted(p for d in a.dirs for p in d.glob("*.experts.u16"))
    dists, freq, working = [], np.zeros((a.layers, N_EXPERT)), []
    for f in files:
        trace = load(f, a.layers, a.k)
        dists.append(stack_distances(trace).ravel())
        n_layer = trace.shape[1]
        for layer in range(n_layer):
            freq[layer] += np.bincount(trace[:, layer].ravel(), minlength=N_EXPERT)
        working.append(np.mean([len(np.unique(trace[:, layer])) for layer in range(n_layer)]))
        print(f"{f.name}: {trace.shape[0]} tokens, {n_layer} layers, distinct experts/layer {working[-1]:.0f} of {N_EXPERT}")
    d = np.concatenate(dists)
    n_layer = trace.shape[1]

    print(f"\n{len(files)} documents, {d.size / (n_layer * a.k):.0f} tokens; distinct experts per layer and document: "
          f"median {np.median(working):.0f}, max {max(working):.0f} of {N_EXPERT}")
    shares = np.sort(freq[:n_layer], axis=1)[:, ::-1].cumsum(axis=1) / freq[:n_layer].sum(axis=1, keepdims=True)
    for q in (0.5, 0.8, 0.9, 0.95):
        need = (shares < q).sum(axis=1).mean() + 1
        print(f"global skew: {need:.0f} hottest experts per layer ({need / N_EXPERT:.0%}) carry {q:.0%} of all uses")

    budget_ms = 1000 / a.tps
    print(f"\n| cache/layer | RAM experts | hit rate | SSD MB/token | SSD ms/token (at {a.ssd_gbps:g} GB/s) | vs {budget_ms:.0f} ms/token |")
    print("|---|---|---|---|---|---|")
    for frac in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        cap = int(frac * N_EXPERT)
        hit = (d < cap).mean()
        mb = (1 - hit) * a.k * n_layer * EXPERT_MB
        ms = mb / (a.ssd_gbps * 1000) * 1000
        ram_gb = cap * EXPERT_MB * a.layers / 1000
        print(f"| {cap} ({frac:.0%}) | {ram_gb:.1f} GB | {hit:.1%} | {mb:.0f} | {ms:.1f} | {ms / budget_ms:.0%} |")


if __name__ == "__main__":
    main()
