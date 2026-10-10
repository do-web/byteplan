"""Checks for bin/run's address parsing and file picking (no network): python3 tools/test_run.py"""
import importlib.machinery
import importlib.util
import json
import tempfile
from pathlib import Path

path = str(Path(__file__).resolve().parents[1] / "bin" / "run")
spec = importlib.util.spec_from_loader("run", importlib.machinery.SourceFileLoader("run", path))
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)

assert run.parse("Qwen/Qwen3-8B-GGUF") == ("Qwen/Qwen3-8B-GGUF", None, None)
assert run.parse("Qwen/Qwen3-8B-GGUF:q4_k_m") == ("Qwen/Qwen3-8B-GGUF", "q4_k_m", None)
assert run.parse("https://huggingface.co/Qwen/Qwen3-8B/tree/main") == ("Qwen/Qwen3-8B", None, None)
assert run.parse("hf.co/a/b-GGUF/blob/main/x/b-Q8_0.gguf") == ("a/b-GGUF", "x/b-Q8_0.gguf", None)
assert run.parse("qwen3") == (None, None, None)
assert run.parse("https://huggingface.co/a/b/resolve/main/x-Q8_0.gguf?download=true") == ("a/b", "x-Q8_0.gguf", None)
assert run.parse("a/b-GGUF/x.gguf") == ("a/b-GGUF", "x.gguf", None)
assert run.tag_of("Q4_K_M/m-UD-Q4_K_XL-00001-of-00002.gguf") == "UD-Q4_K_XL"
assert run.tag_of("model.Q8_0.gguf") == "Q8_0" and run.tag_of("mmproj-f16.gguf") == "F16"

# default pick: Q8_0 when it fits, else the biggest quant that fits; vision + MTP sidecars ride along
files = [{"path": p, "size": s} for p, s in [("m-Q4_K_M.gguf", 4), ("m-Q8_0.gguf", 8), ("m-BF16.gguf", 16),
                                             ("mmproj-F16.gguf", 1), ("mmproj-F32.gguf", 2), ("mtp-m-Q8_0.gguf", 1)]]
got = []
run.hf_download = lambda repo, f, dest: got.extend(f)
run.check_disk = lambda *a: None
run.BUDGET = 20
assert run.gguf_repo("a/b", None, files)[0].name == "m-Q8_0.gguf"
assert sorted(got) == ["m-Q8_0.gguf", "mmproj-F16.gguf", "mtp-m-Q8_0.gguf"], got
run.BUDGET = 7
assert run.gguf_repo("a/b", None, files)[0].name == "m-Q4_K_M.gguf"
# draft heads and imatrix files next to the model are never picked as the model
files += [{"path": p, "size": s} for p, s in [("dflash-m-Q8_0.gguf", 1), ("eagle3-m-Q8_0.gguf", 1), ("imatrix_m.gguf", 1)]]
assert run.gguf_repo("a/b", None, files)[0].name == "m-Q4_K_M.gguf"
assert run.gguf_repo("a/b", "bf16", files)[0].name == "m-BF16.gguf"

with tempfile.TemporaryDirectory() as d:
    (Path(d) / "config.json").write_text(json.dumps({"auto_map": {"AutoModel": "x--y.Z"}, "a": 1}))
    run.strip_remote_code(Path(d))
    assert json.loads((Path(d) / "config.json").read_text()) == {"a": 1}
print("ok")
