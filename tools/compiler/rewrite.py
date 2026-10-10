#!/usr/bin/env python3
"""-O1 "dense-q8": streaming GGUF rewriter for qwen4exp.

Requantizes the hyper-connection matmuls (float -> Q8_0); the MoE router and the lm_head only on request, each
a separately measured lossy switch. Header, KV metadata and all other tensors are copied byte for byte, further
shards are hard-linked.
The output is verified against the source before it gets its final name.
"""
import argparse
import ctypes
import functools
import hashlib
import os
import re
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from gguf import GGML_QUANT_SIZES, GGUFReader, quants
from gguf import GGMLQuantizationType as T
from gguf.gguf_writer import SHARD_NAME_FORMAT

HERE = Path(__file__).resolve().parent
GGML_BASE = HERE.parents[1] / "build/ggml/src/libggml-base.a"
GGML_DYLIB = HERE / ".build/libggml-quant.dylib"

# Targets, names from vendor/llama.cpp/src/llama-arch.cpp (LLM_ARCH_QWEN4EXP); all are GGML_OP_MUL_MAT
# weights read in full for every token:
#   blk.N.hc_{attn,ffn}_{down,up,inject}.weight, output_hc_{down,up}.weight, MTP blk.N.nextn.hc_head_{down,up}.weight
#   --router: blk.N.ffn_gate_inp.weight (llama-quantize never quantizes it, so gguf-py does it here)
# Not targets: hc_*_norm (GGML_OP_MUL), ffn_gate_inp_shexp (1-D), other BF16 (indexer, ssm_alpha/beta, ple_value).
HC = re.compile(r"hc_((attn|ffn|head)_)?(down|up|inject)\.weight$")
ROUTER = re.compile(r"ffn_gate_inp\.weight$")
LM_HEAD = "output.weight"
FLOAT = {T.F32, T.F16, T.BF16}
SPLIT = re.compile(r"-(\d{5})-of-(\d{5})\.gguf$")
CHUNK = 32 << 20  # bytes per read / float32 bytes per conversion step, bounds peak RSS
MIN_FREE = 30 << 30  # bin/run-guarded preflight minimum, must still hold after writing


def need(ok: bool, msg: str) -> None:
    if not ok:
        sys.exit(f"Error: {msg}")


def nbytes(qtype: T, n_elements: int) -> int:
    block, size = GGML_QUANT_SIZES[qtype]
    return n_elements // block * size


def plan(reader: GGUFReader, dense: T, router: T | None, lm_head: T | None) -> list[tuple]:
    """(tensor, new_type) in file order; new_type == tensor_type means byte copy."""
    out = []
    for t in reader.tensors:
        new = t.tensor_type
        if t.name == LM_HEAD and lm_head:
            need(t.tensor_type in FLOAT, f"{LM_HEAD} is {t.tensor_type.name}; --lm-head only from F32/F16/BF16, "
                 "requantizing adds to the error and usually costs more bytes here")
            new = lm_head
        elif t.tensor_type in FLOAT and HC.search(t.name):
            new = dense
        elif t.tensor_type in FLOAT and router and ROUTER.search(t.name):
            new = router
        if new != t.tensor_type and int(t.shape[0]) % GGML_QUANT_SIZES[new][0]:
            print(f"Warning: {t.name} ne0={t.shape[0]} not divisible by the {new.name} block size, kept", file=sys.stderr)
            new = t.tensor_type
        out.append((t, new))
    return out


def read(fd: int, offset: int, n: int):
    end = offset + n
    while offset < end:
        b = os.pread(fd, min(CHUNK, end - offset), offset)
        if not b:
            raise EOFError(f"file ends at {offset}, expected {end}")
        offset += len(b)
        yield b


def f32_rows(fd: int, t):
    """Dequantized float32 row blocks of tensor t, at most CHUNK bytes each."""
    ne0 = int(t.shape[0])
    rows = t.n_elements // ne0
    row = t.n_bytes // rows
    step = max(1, CHUNK // (4 * ne0))
    for r in range(0, rows, step):
        n = min(step, rows - r)
        raw = np.frombuffer(b"".join(read(fd, t.data_offset + r * row, n * row)), np.uint8).reshape(n, row)
        yield quants.dequantize(raw, t.tensor_type)


@functools.cache
def ggml_quantize_chunk():
    """ggml_quantize_chunk from build/ggml/src/libggml-base.a (GGML_BASE), linked once into a dylib."""
    if not GGML_DYLIB.exists() or GGML_DYLIB.stat().st_mtime < GGML_BASE.stat().st_mtime:
        GGML_DYLIB.parent.mkdir(exist_ok=True)
        subprocess.run(["cc", "-dynamiclib", "-o", GGML_DYLIB, "-Wl,-u,_ggml_quantize_chunk", GGML_BASE, "-lc++"], check=True)
    f = ctypes.CDLL(str(GGML_DYLIB)).ggml_quantize_chunk
    f.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, ctypes.c_void_p]
    f.restype = ctypes.c_size_t
    return f


def ggml_quantize(x: np.ndarray, qtype: T) -> np.ndarray:
    x = np.ascontiguousarray(x, np.float32)
    out = np.empty((x.shape[0], nbytes(qtype, x.shape[1])), np.uint8)
    n = ggml_quantize_chunk()(qtype, x.ctypes.data, out.ctypes.data, 0, *x.shape, None)
    need(n == out.nbytes, f"ggml_quantize_chunk {qtype.name}: {n} instead of {out.nbytes} bytes")
    return out


def quantize(x: np.ndarray, qtype: T) -> np.ndarray:
    try:
        return quants.quantize(x, qtype)  # gguf-py: Q8_0, bit-identical to ggml (test_rewrite.py)
    except NotImplementedError:  # e.g. Q6_K: only ggml itself
        return ggml_quantize(x, qtype)


def metadata(reader: GGUFReader, steps: list[tuple]) -> tuple[bytes, list[int]]:
    """Header + KV bytes unchanged, tensor infos with new type and offset, padded; plus the data offsets."""
    align = reader.alignment
    infos, offsets, off = [], [], 0
    for t, new in steps:
        f = t.field
        raw = bytes(reader.data[f.offset : f.offset + sum(p.nbytes for p in f.parts)])
        infos.append(raw[:-12] + struct.pack("<IQ", new, off))  # info ends with u32 type, u64 offset
        offsets.append(off)
        off += nbytes(new, t.n_elements)
        off += -off % align
    meta = bytes(reader.data[: steps[0][0].field.offset]) + b"".join(infos)
    return meta + bytes(-len(meta) % align), offsets + [off]


def write(src: Path, steps: list[tuple], meta: bytes, offsets: list[int], dst: Path) -> None:
    with open(src, "rb") as fin, open(dst, "xb") as fout:
        fout.write(meta)
        for (t, new), off in zip(steps, offsets):
            fout.write(bytes(len(meta) + off - fout.tell()))  # alignment padding
            if new == t.tensor_type:
                fout.writelines(read(fin.fileno(), t.data_offset, t.n_bytes))
            else:
                fout.writelines(quantize(x, new).tobytes() for x in f32_rows(fin.fileno(), t))
        fout.write(bytes(len(meta) + offsets[-1] - fout.tell()))


def sha256(fd: int, t) -> str:
    h = hashlib.sha256()
    for b in read(fd, t.data_offset, t.n_bytes):
        h.update(b)
    return h.hexdigest()


def verify(src: Path, reader: GGUFReader, steps: list[tuple], dst: Path) -> None:
    """Header/KV bytes equal, same tensors; unchanged tensors sha256-equal, changed ones within quantization error."""
    b = GGUFReader(dst)
    kv_end = steps[0][0].field.offset
    need(bytes(reader.data[:kv_end]) == bytes(b.data[:kv_end]), "header/KV differ")
    need(len(b.tensors) == len(steps), "tensor count differs")
    worst = {}
    with open(src, "rb") as fa, open(dst, "rb") as fb:
        for (t, new), u in zip(steps, b.tensors):
            need((u.name, u.shape.tolist(), u.tensor_type) == (t.name, t.shape.tolist(), new), f"tensor info {t.name}")
            if new == t.tensor_type:
                need(sha256(fa.fileno(), t) == sha256(fb.fileno(), u), f"{t.name} not byte-identical")
                continue
            err = sq = 0.0
            for x, y in zip(f32_rows(fa.fileno(), t), f32_rows(fb.fileno(), u)):
                err += float(np.square(x - y, dtype=np.float64).sum())
                sq += float(np.square(x, dtype=np.float64).sum())
            rel = (err / sq) ** 0.5 if sq else 0.0
            need(rel < 0.05, f"{t.name}: rel. RMSE {rel:.4f}")
            key = f"{t.tensor_type.name}->{new.name}"
            worst[key] = max(worst.get(key, 0.0), rel)
    n_same = sum(new == t.tensor_type for t, new in steps)
    print(f"verify ok: header/KV byte-identical, {n_same} unchanged tensors sha256-identical, "
          f"max rel. RMSE {', '.join(f'{k} {v:.4f}' for k, v in worst.items()) or '-'}")


def report(steps: list[tuple], src_size: int, out_size: int) -> None:
    changed = [(t, new) for t, new in steps if new != t.tensor_type]
    print(f"{'Tensor':44} {'Shape':>14} {'old':>6} {'new':>6} {'old MB':>9} {'new MB':>9}")
    for t, new in changed:
        shape = "x".join(map(str, t.shape.tolist()))
        print(f"{t.name:44} {shape:>14} {t.tensor_type.name:>6} {new.name:>6} "
              f"{t.n_bytes / 1e6:9.2f} {nbytes(new, t.n_elements) / 1e6:9.2f}")
    delta = {}
    for t, new in changed:
        g = "lm_head" if t.name == LM_HEAD else "Router" if ROUTER.search(t.name) else "HC"
        delta[g] = delta.get(g, 0) + nbytes(new, t.n_elements) - t.n_bytes
    rest = [t for t, new in steps if new == t.tensor_type and t.tensor_type in {T.F16, T.BF16} and len(t.shape) > 1]
    print(f"changed: {len(changed)} of {len(steps)} tensors; Δ per token {sum(delta.values()) / 1e9:+.4f} GB "
          f"({', '.join(f'{g} {d / 1e9:+.4f}' for g, d in delta.items()) or '-'}; "
          f"every target is read in full per token, so = Δ file)")
    print(f"still F16/BF16 (not targets): {len(rest)} tensors, {sum(t.n_bytes for t in rest) / 1e9:.4f} GB")
    print(f"Shard 1: {src_size / 1e9:.4f} GB -> {out_size / 1e9:.4f} GB")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="src", type=Path, required=True, help="GGUF or shard 1 (*-00001-of-0000N.gguf)")
    ap.add_argument("--out", type=Path, required=True, help="output directory (same volume, hard links)")
    ap.add_argument("--dense", choices=["q8_0"], default="q8_0", help="type for the HC matmuls")
    ap.add_argument("--router", choices=["keep", "q8_0"], default="keep", help="MoE router ffn_gate_inp")
    ap.add_argument("--lm-head", choices=["keep", "q8_0", "q6_K"], default="keep", help="only from F32/F16/BF16")
    ap.add_argument("--dry-run", action="store_true", help="only show the plan and the savings")
    args = ap.parse_args()
    t0 = time.monotonic()

    reader = GGUFReader(args.src)
    need(reader.byte_order == "I" and sys.byteorder == "little", "little-endian GGUF only")
    arch = reader.fields.get("general.architecture")
    need(arch is not None and arch.contents() == "qwen4exp", f"qwen4exp only, not {arch and arch.contents()}")
    dense, router, lm_head = (None if a == "keep" else T[a.upper()] for a in (args.dense, args.router, args.lm_head))
    steps = plan(reader, dense, router, lm_head)
    if lm_head and not any(t.name == LM_HEAD for t, _ in steps):
        print(f"Warning: no {LM_HEAD} (tied embeddings), --lm-head has no effect", file=sys.stderr)

    count = int(reader.fields["split.count"].contents()) if "split.count" in reader.fields else 1
    switches = {"router": args.router, "lm": args.lm_head}
    tag = f"dense-{args.dense}" + "".join(f"-{k}-{v}" for k, v in switches.items() if v != "keep")
    if count > 1:
        m = SPLIT.search(args.src.name)
        need(m and int(m[1]) == 1 and int(m[2]) == count, f"--in must be shard 1 of {count}")
        prefix = args.src.name[: m.start()]
        srcs = [args.src.with_name(SHARD_NAME_FORMAT.format(prefix, i, count)) for i in range(1, count + 1)]
        dsts = [args.out / SHARD_NAME_FORMAT.format(f"{prefix}-{tag}", i, count) for i in range(1, count + 1)]
    else:
        srcs, dsts = [args.src], [args.out / f"{args.src.stem}-{tag}.gguf"]
    for s in srcs[1:]:  # further shards are linked unchanged, so they must not contain targets
        if not s.exists():
            need(args.dry_run, f"{s} is missing")
            print(f"Warning: {s.name} is missing, target tensors in it not checked", file=sys.stderr)
            continue
        hits = [t.name for t, new in plan(GGUFReader(s), dense, router, lm_head) if new != t.tensor_type]
        need(not hits, f"{s.name} contains target tensors ({hits[:3]}…), not supported")
    meta, offsets = metadata(reader, steps)
    out_size = len(meta) + offsets[-1]
    report(steps, reader.data.nbytes, out_size)
    print("Output: " + ", ".join(d.name for d in dsts))
    if args.dry_run:
        return

    args.out.mkdir(parents=True, exist_ok=True)
    for d in dsts:
        need(not d.exists(), f"{d} already exists")
    need(count == 1 or srcs[1].stat().st_dev == args.out.stat().st_dev,  # fail before writing, not at os.link
         "--out must be on the same volume as the source (hard links)")
    free = shutil.disk_usage(args.out).free
    need(free - out_size >= MIN_FREE, f"disk: {free / 2**30:.0f} GiB free, < {MIN_FREE >> 30} GiB after writing")
    part = dsts[0].with_name(dsts[0].name + ".part")
    try:
        write(args.src, steps, meta, offsets, part)
        t1 = time.monotonic()
        verify(args.src, reader, steps, part)
        for s, d in zip(srcs[1:], dsts[1:]):
            os.link(s, d)
    except BaseException:
        for d in [part, *dsts[1:]]:
            d.unlink(missing_ok=True)
        raise
    part.chmod(0o444)  # models are read-only once checked
    part.rename(dsts[0])
    print(f"done: write {t1 - t0:.1f} s, verify {time.monotonic() - t1:.1f} s, "
          f"{dsts[0].stat().st_size / 1e9:.4f} GB")


if __name__ == "__main__":
    main()
