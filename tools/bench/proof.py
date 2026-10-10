#!/usr/bin/env python3
"""Byteplan vs stock llama.cpp on the same Mac: decode speed per task, prompt reading, time to first token of an
agent chat, with a hash of every answer (greedy) so you can see which setups give identical text.

Each configuration runs its own llama-server (127.0.0.1:8090) through bin/run-guarded; the configurations alternate
over the rounds (A B C D, then D C B A, ...) and the report shows the median. Standard library only.

  tools/bench/proof.py --stock-bin <llama.cpp>/build/bin/llama-server --rounds 2 --out bench/proof.md
"""
import argparse
import base64
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORT = 8090
BASE = f"http://127.0.0.1:{PORT}"
CODE = (ROOT / "tools" / "experts" / "simulate.py").read_text()

TASKS = [
    ("edit code", "code-edit",
     f"Here is a Python file:\n\n```python\n{CODE}\n```\n\nReturn the complete file unchanged, only rename the function "
     "`stack_distances` to `reuse_distances` (also where it is called). Only the code, no explanation."),
    ("refactor (agent)", "agent-refactor",
     f"```python\n{CODE}\n```\n\nAdd a short docstring to every function and return the complete file."),
    ("write new code", "code-new",
     "Write a Python class for a priority queue based on heapq, including pytest tests."),
    ("write prose", "prose",
     "Write a factual text of about 400 words about the history of the railway in Germany."),
]


def post(path, body, timeout=1800):
    req = urllib.request.Request(BASE + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def long_document(chars=24000):
    """~6k tokens of this repository's own source code (same text on every machine)."""
    parts = []
    for f in sorted((ROOT / "tools").rglob("*.py")):
        parts.append(f"# {f.relative_to(ROOT)}\n{f.read_text()}")
        if sum(map(len, parts)) >= chars:
            break
    return "".join(parts)[:chars]


def mtp_draft(models: Path) -> Path:
    """Byteplan's draft model: the MTP head with the 2-bit vocabulary head from install.sh (stock uses the plain one)."""
    head2 = models / "mtp" / "Qwen3.8-Flash-Next-MTP-Q4_K_M-head2.gguf"
    if not head2.exists():
        raise SystemExit(f"{head2} is missing, run ./install.sh")
    return head2


def chat(messages, n, tools=None):
    body = {"messages": messages, "max_tokens": n, "temperature": 0, "stream": False,
            "chat_template_kwargs": {"enable_thinking": False}}
    if tools:
        body["tools"] = tools
    d = post("/v1/chat/completions", body)
    return d.get("timings", {}), d["choices"][0]["message"].get("content") or ""


def run_config(cfg, args, tools):
    env = dict(os.environ, BYTEPLAN_MODELS=args.models, **cfg.get("env", {}))
    # ponytail: profile parallel (exclusive also refuses old swap, which most Macs have); plug in power and close big apps
    cmd = [str(ROOT / "bin" / "run-guarded"), "--profile", "parallel", "--need-gb", "42", "--",
           cfg["bin"], "-lm", "mmap", "-lzm", "on", "-np", "1", "--cache-ram", "0", "-c", "16384",
           "-ub", str(args.ub), "-b", str(args.ub),  # the --spar configs set 2048 again below
           "--host", "127.0.0.1", "--port", str(PORT), *cfg["args"]]
    log = Path(args.logdir) / f"server-{cfg['name']}.log"
    with open(log, "a") as out:
        proc = subprocess.Popen(cmd, env=env, stdout=out, stderr=subprocess.STDOUT)
    try:
        for _ in range(600):
            try:
                urllib.request.urlopen(BASE + "/health", timeout=2)
                break
            except Exception:
                if proc.poll() is not None:
                    raise RuntimeError(f"{cfg['name']}: server did not start, see {log}")
                time.sleep(0.5)
        else:
            raise RuntimeError(f"{cfg['name']}: server not ready after 5 minutes, see {log}")
        res = {"decode": {}, "hash": {}}
        for label, key, prompt in TASKS:
            t, text = chat([{"role": "user", "content": prompt}], 900)
            res["decode"][key] = t["predicted_per_second"]
            res["hash"][key] = hashlib.md5(text.encode()).hexdigest()[:8]
            print(f"  {cfg['name']:<22} {label:<18} {t['predicted_per_second']:6.1f} tok/s  #{res['hash'][key]}", flush=True)
        d = post("/completion", {"prompt": long_document(), "n_predict": 1, "cache_prompt": False})
        res["prefill"] = d["timings"]["prompt_per_second"]
        res["prefill_tokens"] = d["timings"]["prompt_n"]
        # a new agent chat: the web UI of Byteplan prewarms the system+tools start once after the page loads
        if cfg.get("prewarm"):
            chat([{"role": "user", "content": ""}], 1, tools)
        t, _ = chat([{"role": "user", "content": "Explain in two sentences what a mutex is."}], 60, tools)
        res["ttft_s"] = t.get("prompt_ms", 0) / 1000
        res["ttft_tokens"] = t.get("prompt_n")
        print(f"  {cfg['name']:<22} prompt {res['prefill']:6.0f} tok/s, new agent chat {res['ttft_s']:.2f} s", flush=True)
        return res
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", default=os.environ.get("BYTEPLAN_MODELS", str(Path.home() / "byteplan-models")))
    ap.add_argument("--stock-bin", required=True, help="llama-server of an unmodified llama.cpp build")
    ap.add_argument("--byteplan-bin", default=str(ROOT / "build" / "bin" / "llama-server"))
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--ub", type=int, default=512, help="prompt chunk size for all configs (bin/chat uses 2048 up to 64k context)")
    ap.add_argument("--only", default="", help="comma-separated config names")
    ap.add_argument("--out", default=str(ROOT / "bench" / "proof.md"))
    ap.add_argument("--logdir", default=str(ROOT / "logs" / "proof"))
    args = ap.parse_args()
    Path(args.logdir).mkdir(parents=True, exist_ok=True)

    m = Path(args.models)
    o1 = str(m / "ista-o1" / "Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-dense-q8_0-router-q8_0-00001-of-00002.gguf")
    sp = m / "ista-o1-spar" / "Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-dense-q8_0-router-q8_0-spar"
    mtp = ["-md", str(m / "mtp" / "Qwen3.8-Flash-Next-MTP-Q4_K_M.gguf"), "--spec-draft-n-max", "3"]
    mtp_bp = ["-md", str(mtp_draft(m)), "--spec-draft-n-max", "3"]
    ours = {"GGML_METAL_N_CB": "8"}
    spar = ["-m", f"{sp}-00001-of-00002.gguf", "--spar-experts", f"{sp}.experts.bin", *mtp_bp,
            "--spec-type", "draft-mtp,ngram-mod", "-ub", "2048", "-b", "2048"]
    configs = [
        {"name": "llama.cpp (stock)", "bin": args.stock_bin, "args": ["-m", o1, *mtp, "--spec-type", "draft-mtp"]},
        # reference for the checksums: no drafts at all, one token per step
        {"name": "llama.cpp, no drafts", "bin": args.stock_bin, "args": ["-m", o1]},
        {"name": "Byteplan", "bin": args.byteplan_bin, "env": ours, "prewarm": True,
         "args": ["-m", o1, *mtp_bp, "--spec-type", "draft-mtp,ngram-mod"]},
        *({"name": f"Byteplan --spar {n}", "bin": args.byteplan_bin, "env": ours, "prewarm": True,
           "args": [*spar, "--spar-slots", str(n)]} for n in (410, 358)),
    ]
    if args.only:
        keep = {s.strip() for s in args.only.split(",")}
        configs = [c for c in configs if c["name"] in keep]

    tools = json.loads((ROOT / "tools" / "bench" / "agent-tools.json").read_text())
    tools += [{"type": "function", "function": {"name": "get_datetime", "description": "Get the current date and time.",
                                                "parameters": {"type": "object", "properties": {}}}}]
    runs = {c["name"]: [] for c in configs}
    for r in range(args.rounds):
        order = configs if r % 2 == 0 else list(reversed(configs))
        print(f"round {r + 1}/{args.rounds}", flush=True)
        for cfg in order:
            runs[cfg["name"]].append(run_config(cfg, args, tools))

    names = [c["name"] for c in configs]

    def col(key, fmt):
        return " | ".join(format(statistics.median(x[key] for x in runs[n]), fmt) for n in names)

    chip = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    ram = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout) >> 30
    lines = [f"Measured on {chip or platform.machine()} {ram} GB, macOS {platform.mac_ver()[0]}, median of {args.rounds} rounds, "
             f"{time.strftime('%Y-%m-%d')}. Greedy answers; the hash shows identical text.\n",
             "| Task (tokens/s) | " + " | ".join(names) + " |", "|---|" + "---:|" * len(names)]
    for label, key, _ in TASKS:
        cells = [f"{statistics.median(x['decode'][key] for x in runs[n]):.0f} `#{runs[n][0]['hash'][key]}`" for n in names]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines.append(f"| read a long prompt | {col('prefill', '.0f')} |")
    lines.append(f"| new agent chat, seconds before writing | {col('ttft_s', '.2f')} |")
    Path(args.out).write_text("\n".join(lines) + "\n")
    Path(args.out).with_suffix(".json").write_text(json.dumps(runs, indent=1))
    print("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
