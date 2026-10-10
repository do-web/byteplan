#!/usr/bin/env python3
"""Byteplan vs sushi on this Mac: same 4 tasks as tools/bench/proof.py, measured the same way on the client
(streaming: tokens/s between first and last token), plus prompt reading and a new agent chat after a prewarm.

  tools/bench/vs_sushi.py --sushi-bin <sushi>/zig-out/bin/sushi --sushi-model ~/.sushi/models/Qwen3.8-Flash-Next-Sushi-2bpw --rounds 2
"""
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import argparse

OSS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(OSS / "tools/bench"))
import proof  # noqa: E402  (TASKS, long_document, mtp_draft)

PORT = 8090
BASE = f"http://127.0.0.1:{PORT}"
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--sushi-bin", required=True)
ap.add_argument("--sushi-model", required=True)
ap.add_argument("--models", default=os.environ.get("BYTEPLAN_MODELS", str(Path.home() / "byteplan-models")))
ap.add_argument("--rounds", type=int, default=2)
ap.add_argument("--out", default=str(OSS / "bench"))
ARGS = ap.parse_args()
SCR = Path(ARGS.out)
SCR.mkdir(parents=True, exist_ok=True)
M = Path(ARGS.models)
SUSHI = Path(ARGS.sushi_bin)
SUSHI_MODEL = Path(ARGS.sushi_model)
O1 = M / "ista-o1/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-dense-q8_0-router-q8_0-00001-of-00002.gguf"
MTP = proof.mtp_draft(M)

CONFIGS = [
    {"name": "Byteplan", "env": {"GGML_METAL_N_CB": "8"},
     "cmd": [str(OSS / "build/bin/llama-server"), "-m", str(O1), "-md", str(MTP), "--spec-type", "draft-mtp,ngram-mod",
             "--spec-draft-n-max", "3", "-lm", "mmap", "-lzm", "on", "-np", "1", "--cache-ram", "0", "--ctx-checkpoints", "8",
             "--checkpoint-min-step", "1024", "-c", "16384", "-ub", "2048", "-b", "2048", "--host", "127.0.0.1", "--port", str(PORT)]},
    {"name": "sushi 2bpw (default)", "env": {},
     "cmd": [str(SUSHI), "--serve", "--model", str(SUSHI_MODEL), "--host", "127.0.0.1", "--port", str(PORT),
             "--ctx-size", "16384", "--no-vision", "--prefix-cache-disk", "0", "--no-update-check"]},
    {"name": "sushi 2bpw (lossless)", "env": {},
     "cmd": [str(SUSHI), "--serve", "--model", str(SUSHI_MODEL), "--host", "127.0.0.1", "--port", str(PORT),
             "--ctx-size", "16384", "--no-vision", "--prefix-cache-disk", "0", "--no-update-check",
             "--kv-quant", "16", "--no-decode-attn-quant"]},
]


def stream(messages, n, tools=None):
    """-> (text, completion tokens, seconds to first token, decode tokens/s between first and last token)"""
    body = {"model": "qwen", "messages": messages, "max_tokens": n, "temperature": 0, "stream": True,
            "stream_options": {"include_usage": True}, "chat_template_kwargs": {"enable_thinking": False}}
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(BASE + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.perf_counter()
    first = last = None
    text, chunks, usage = [], 0, None
    with urllib.request.urlopen(req, timeout=1800) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            d = json.loads(line[5:])
            usage = d.get("usage") or usage
            for ch in d.get("choices", []):
                delta = ch.get("delta", {})
                piece = (delta.get("content") or "") + (delta.get("reasoning_content") or "")
                if piece or delta.get("tool_calls"):
                    now = time.perf_counter()
                    first = first or now
                    last = now
                    chunks += 1
                    text.append(piece)
    n_tok = (usage or {}).get("completion_tokens") or chunks
    dt = (last - first) if first and last and last > first else float("nan")
    return "".join(text), n_tok, (first - t0) if first else float("nan"), (n_tok - 1) / dt


def prompt_speed():
    doc = proof.long_document()
    body = {"model": "qwen", "messages": [{"role": "user", "content": doc + "\n\nSummarize in one word."}], "max_tokens": 1,
            "temperature": 0, "stream": False, "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(BASE + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.perf_counter()
    d = json.load(urllib.request.urlopen(req, timeout=1800))
    wall = time.perf_counter() - t0
    n = d.get("usage", {}).get("prompt_tokens") or d.get("timings", {}).get("prompt_n")
    return n / wall, n


def run(cfg, tools, logdir):
    log = logdir / f"{cfg['name'].replace(' ', '_')}.log"
    with open(log, "a") as out:
        proc = subprocess.Popen([str(OSS / "bin/run-guarded"), "--profile", "parallel", "--need-gb", "40", "--", *cfg["cmd"]],
                                env=dict(os.environ, BYTEPLAN_MODELS=str(M), **cfg["env"]), stdout=out, stderr=subprocess.STDOUT)
    try:
        t_load = time.perf_counter()
        for _ in range(1800):
            try:
                urllib.request.urlopen(BASE + "/health", timeout=2)
                break
            except Exception:
                if proc.poll() is not None:
                    raise RuntimeError(f"{cfg['name']} did not start, see {log}")
                time.sleep(0.5)
        else:
            raise RuntimeError(f"{cfg['name']} not ready after 15 min")
        res = {"load_s": time.perf_counter() - t_load, "decode": {}, "hash": {}, "tokens": {}}
        for label, key, prompt in proof.TASKS:
            text, n, _, tps = stream([{"role": "user", "content": prompt}], 900)
            res["decode"][key], res["tokens"][key] = tps, n
            res["hash"][key] = hashlib.md5(text.encode()).hexdigest()[:8]
            print(f"  {cfg['name']:<24} {label:<18} {tps:6.1f} tok/s  ({n} tok) #{res['hash'][key]}", flush=True)
        try:
            res["prefill"], res["prefill_tokens"] = prompt_speed()
        except Exception as e:
            print(f"  {cfg['name']}: prompt test failed: {e}", flush=True)
            res["prefill"], res["prefill_tokens"] = float("nan"), 0
        try:
            stream([{"role": "user", "content": "."}], 1, tools)  # prewarm the system + tools start (sushi rejects an empty message)
            _, _, ttft, _ = stream([{"role": "user", "content": "Explain in two sentences what a mutex is."}], 60, tools)
        except Exception as e:
            print(f"  {cfg['name']}: agent chat test failed: {e}", flush=True)
            ttft = float("nan")
        res["ttft_s"] = ttft
        print(f"  {cfg['name']:<24} prompt {res['prefill']:6.0f} tok/s ({res['prefill_tokens']} tok), agent chat {ttft:.2f} s,"
              f" load {res['load_s']:.0f} s", flush=True)
        return res
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=90)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    rounds = ARGS.rounds
    logdir = SCR / "vs-sushi-logs"
    logdir.mkdir(exist_ok=True)
    tools = json.loads((OSS / "tools/bench/agent-tools.json").read_text())
    runs = {c["name"]: [] for c in CONFIGS}
    for r in range(rounds):
        print(f"round {r + 1}/{rounds}", flush=True)
        for cfg in CONFIGS if r % 2 == 0 else CONFIGS[::-1]:
            while "AC Power" not in subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout:
                print("  waiting for AC power", flush=True)
                time.sleep(60)
            runs[cfg["name"]].append(run(cfg, tools, logdir))
    (SCR / "vs-sushi.json").write_text(json.dumps(runs, indent=1))
    names = [c["name"] for c in CONFIGS]
    med = statistics.median
    lines = ["| Task (tokens/s) | " + " | ".join(names) + " |", "|---|" + "---:|" * len(names)]
    for label, key, _ in proof.TASKS:
        lines.append(f"| {label} | " + " | ".join(f"{med(x['decode'][key] for x in runs[n]):.0f} `#{runs[n][0]['hash'][key]}`" for n in names) + " |")
    lines.append("| read a long prompt | " + " | ".join(f"{med(x['prefill'] for x in runs[n]):.0f}" for n in names) + " |")
    lines.append("| new agent chat (s) | " + " | ".join(f"{med(x['ttft_s'] for x in runs[n]):.2f}" for n in names) + " |")
    lines.append("| load (s) | " + " | ".join(f"{med(x['load_s'] for x in runs[n]):.0f}" for n in names) + " |")
    (SCR / "vs-sushi.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
