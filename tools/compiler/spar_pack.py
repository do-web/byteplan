#!/usr/bin/env python3
"""spar-pack: split a qwen4exp GGUF into a trunk without routed experts plus an expert file for the
expert pool (stage 2, see `bin/chat --spar`).

- Trunk: same GGUF minus the `blk.N.ffn_{gate,up,down}_exps.weight` tensors (header tensor count patched,
  KV metadata and all other tensors byte for byte); further shards are hard-linked.
- `experts.bin`: per layer and expert one blob gate|up|down (each the expert's contiguous slice of the source
  tensor), blob stride and file layout aligned to 16 KiB, so one pread per expert fills a pool slot exactly.

Layout of experts.bin (little-endian), 16 KiB header:
  "BPEXPRT1", u32 version=1, u32 n_layer, u32 n_expert, u32 n_mat=3,
  n_mat x { u32 ggml_type, u64 ne0, u64 ne1, u64 slice_bytes, u64 offset_in_blob },
  u64 blob_stride, u64 data_offset, n_layer x u8 present;
  blob(l, e) at data_offset + (l * n_expert + e) * blob_stride.
Everything is verified against the source (sha256 per tensor) before the files get their final names.
"""
import argparse
import hashlib
import os
import re
import shutil
import struct
import sys
import time
from pathlib import Path

from gguf import GGUFReader
from gguf.gguf_writer import SHARD_NAME_FORMAT

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rewrite import MIN_FREE, SPLIT, need, read  # noqa: E402

EXPS = re.compile(r"^blk\.(\d+)\.ffn_(gate|up|down)_exps\.weight$")
MATS = ("gate", "up", "down")
PAGE = 16 << 10
MAGIC = b"BPEXPRT1"


def experts_by_layer(reader: GGUFReader) -> dict[int, dict[str, object]]:
    layers: dict[int, dict[str, object]] = {}
    for t in reader.tensors:
        if m := EXPS.match(t.name):
            layers.setdefault(int(m[1]), {})[m[2]] = t
    for i, mats in layers.items():
        need(set(mats) == set(MATS), f"layer {i}: expert tensors incomplete ({sorted(mats)})")
    return layers


def trunk_metadata(reader: GGUFReader, keep: list) -> tuple[bytes, list[int]]:
    """Header (tensor count patched) + KV unchanged, kept tensor infos with new offsets, padded; data offsets."""
    align = reader.alignment
    infos, offsets, off = [], [], 0
    for t in keep:
        f = t.field
        raw = bytes(reader.data[f.offset : f.offset + sum(p.nbytes for p in f.parts)])
        infos.append(raw[:-8] + struct.pack("<Q", off))  # tensor info ends with u64 offset
        offsets.append(off)
        off += t.n_bytes
        off += -off % align
    head = bytearray(reader.data[: reader.tensors[0].field.offset])
    need(bytes(head[:4]) == b"GGUF" and struct.unpack_from("<I", head, 4)[0] == 3, "GGUF v3 only")
    struct.pack_into("<Q", head, 8, len(keep))  # header: magic, u32 version, u64 n_tensors, u64 n_kv
    if (f := reader.fields.get("split.tensors.count")) is not None:  # total over all shards, checked by the loader
        value = f.parts[f.data[0]]
        at = value.ctypes.data - reader.data.ctypes.data
        head[at : at + value.nbytes] = (value - (len(reader.tensors) - len(keep))).astype(value.dtype).tobytes()
    meta = bytes(head) + b"".join(infos)
    return meta + bytes(-len(meta) % align), offsets + [off]


def write_trunk(src: Path, keep: list, meta: bytes, offsets: list[int], dst: Path) -> None:
    with open(src, "rb") as fin, open(dst, "xb") as fout:
        fout.write(meta)
        for t, off in zip(keep, offsets):
            fout.write(bytes(len(meta) + off - fout.tell()))
            fout.writelines(read(fin.fileno(), t.data_offset, t.n_bytes))
        fout.write(bytes(len(meta) + offsets[-1] - fout.tell()))


def experts_header(layers: dict, n_layer: int, n_expert: int) -> tuple[bytes, int]:
    first = layers[min(layers)]
    head = bytearray(MAGIC + struct.pack("<IIII", 1, n_layer, n_expert, len(MATS)))
    off = 0
    for name in MATS:
        t = first[name]
        slice_bytes = t.n_bytes // n_expert
        head += struct.pack("<IQQQQ", int(t.tensor_type), int(t.shape[0]), int(t.shape[1]), slice_bytes, off)
        off += slice_bytes
    stride = off + (-off % PAGE)
    head += struct.pack("<QQ", stride, PAGE) + bytes(1 if i in layers else 0 for i in range(n_layer))
    need(len(head) <= PAGE, "header too large")
    return bytes(head) + bytes(PAGE - len(head)), stride


def write_experts(src: Path, layers: dict, n_layer: int, n_expert: int, dst: Path) -> int:
    head, stride = experts_header(layers, n_layer, n_expert)
    with open(src, "rb") as fin, open(dst, "xb") as fout:
        fout.write(head)
        for i in range(n_layer):
            mats = layers.get(i)
            if mats is None:
                fout.write(bytes(stride * n_expert))
                continue
            data = {m: b"".join(read(fin.fileno(), t.data_offset, t.n_bytes)) for m, t in mats.items()}
            for e in range(n_expert):
                blob = b"".join(data[m][e * (len(data[m]) // n_expert) : (e + 1) * (len(data[m]) // n_expert)] for m in MATS)
                fout.write(blob + bytes(stride - len(blob)))
    return stride


def sha_file_range(fd: int, offset: int, n: int) -> str:
    h = hashlib.sha256()
    for b in read(fd, offset, n):
        h.update(b)
    return h.hexdigest()


def verify(src: Path, reader: GGUFReader, keep: list, trunk: Path, experts: Path, layers: dict, n_expert: int,
           stride: int) -> None:
    b = GGUFReader(trunk)
    need(len(b.tensors) == len(keep), "trunk: tensor count differs")
    kv_end = reader.tensors[0].field.offset
    a_kv, b_kv = bytearray(reader.data[16:kv_end]), bytearray(b.data[16:kv_end])
    if (f := reader.fields.get("split.tensors.count")) is not None:  # the only KV the trunk changes
        value = f.parts[f.data[0]]
        at = value.ctypes.data - reader.data.ctypes.data - 16
        need(int(b.fields["split.tensors.count"].contents()) == int(f.contents()) - (len(reader.tensors) - len(keep)),
             "trunk: split.tensors.count is wrong")
        a_kv[at : at + value.nbytes] = b_kv[at : at + value.nbytes]
    need(a_kv == b_kv, "trunk: KV metadata differs")
    with open(src, "rb") as fa, open(trunk, "rb") as fb, open(experts, "rb") as fe:
        for t, u in zip(keep, b.tensors):
            need((u.name, u.shape.tolist(), u.tensor_type) == (t.name, t.shape.tolist(), t.tensor_type), f"tensor info {t.name}")
            need(sha_file_range(fa.fileno(), t.data_offset, t.n_bytes) == sha_file_range(fb.fileno(), u.data_offset, u.n_bytes),
                 f"trunk: {t.name} not byte-identical")
        for i, mats in sorted(layers.items()):
            off = 0
            for m in MATS:
                t = mats[m]
                slice_bytes = t.n_bytes // n_expert
                h = hashlib.sha256()
                for e in range(n_expert):
                    blob_at = PAGE + (i * n_expert + e) * stride
                    h.update(os.pread(fe.fileno(), slice_bytes, blob_at + off))
                need(h.hexdigest() == sha_file_range(fa.fileno(), t.data_offset, t.n_bytes), f"experts.bin: {t.name} differs")
                off += slice_bytes
    print(f"verify ok: trunk {len(keep)} tensors sha256-identical, experts.bin {len(layers)} layers x 3 tensors sha256-identical")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="src", type=Path, required=True, help="GGUF or shard 1 (*-00001-of-0000N.gguf)")
    ap.add_argument("--out", type=Path, required=True, help="output directory (same volume, hard links)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    t0 = time.monotonic()

    reader = GGUFReader(args.src)
    arch = reader.fields.get("general.architecture")
    need(arch is not None and arch.contents() == "qwen4exp", "qwen4exp only")
    n_layer = int(reader.fields["qwen4exp.block_count"].contents())
    n_expert = int(reader.fields["qwen4exp.expert_count"].contents())
    layers = experts_by_layer(reader)
    need(layers, "no expert tensors in this shard")
    keep = [t for t in reader.tensors if not EXPS.match(t.name)]
    meta, offsets = trunk_metadata(reader, keep)
    trunk_size = len(meta) + offsets[-1]
    experts_size = PAGE + n_layer * n_expert * experts_header(layers, n_layer, n_expert)[1]

    count = int(reader.fields["split.count"].contents()) if "split.count" in reader.fields else 1
    if count > 1:
        m = SPLIT.search(args.src.name)
        need(m and int(m[1]) == 1 and int(m[2]) == count, f"--in must be shard 1 of {count}")
        prefix = args.src.name[: m.start()]
        srcs = [args.src.with_name(SHARD_NAME_FORMAT.format(prefix, i, count)) for i in range(1, count + 1)]
        dsts = [args.out / SHARD_NAME_FORMAT.format(f"{prefix}-spar", i, count) for i in range(1, count + 1)]
        for s in srcs[1:]:
            need(not experts_by_layer(GGUFReader(s)), f"{s.name} contains experts, not supported")
    else:
        srcs, dsts = [args.src], [args.out / f"{args.src.stem}-spar.gguf"]
    experts = args.out / f"{dsts[0].name.split('-00001-of-')[0].removesuffix('.gguf')}.experts.bin"
    print(f"Trunk {reader.data.nbytes / 1e9:.2f} GB -> {trunk_size / 1e9:.2f} GB ({len(keep)} of {len(reader.tensors)} tensors), "
          f"experts.bin {experts_size / 1e9:.2f} GB ({len(layers)} layers x {n_expert} experts)")
    print("Output: " + ", ".join(d.name for d in [*dsts, experts]))
    if args.dry_run:
        return

    args.out.mkdir(parents=True, exist_ok=True)
    for d in [*dsts, experts]:
        need(not d.exists(), f"{d} already exists")
    need(count == 1 or srcs[1].stat().st_dev == args.out.stat().st_dev, "--out must be on the same volume as the source")
    free = shutil.disk_usage(args.out).free
    need(free - trunk_size - experts_size >= MIN_FREE, f"disk: {free / 2**30:.0f} GiB free, < {MIN_FREE >> 30} GiB afterwards")
    parts = [dsts[0].with_name(dsts[0].name + ".part"), experts.with_name(experts.name + ".part")]
    try:
        write_trunk(args.src, keep, meta, offsets, parts[0])
        stride = write_experts(args.src, layers, n_layer, n_expert, parts[1])
        t1 = time.monotonic()
        verify(args.src, reader, keep, parts[0], parts[1], layers, n_expert, stride)
        for s, d in zip(srcs[1:], dsts[1:]):
            os.link(s, d)
    except BaseException:
        for d in [*parts, *dsts[1:]]:
            d.unlink(missing_ok=True)
        raise
    for p, d in zip(parts, [dsts[0], experts]):
        p.chmod(0o444)
        p.rename(d)
    print(f"done: write {t1 - t0:.1f} s, verify {time.monotonic() - t1:.1f} s")


if __name__ == "__main__":
    main()
