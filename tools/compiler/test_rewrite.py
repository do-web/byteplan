import unittest

import numpy as np
from gguf import GGMLQuantizationType as T
from gguf import quants

from rewrite import HC, ROUTER, ggml_quantize


class RewriteTest(unittest.TestCase):
    def test_q8_0_gguf_py_matches_ggml(self):
        rng = np.random.default_rng(0)
        x = rng.standard_normal((64, 3072), dtype=np.float32) * rng.choice([1e-4, 1.0, 300.0], (64, 1))
        x[0] = 0.0  # all-zero blocks
        x[1, ::7] = 0.5  # exact .5 rounding cases
        self.assertEqual(quants.quantize(x, T.Q8_0).tobytes(), ggml_quantize(x, T.Q8_0).tobytes())

    def test_q6_k_roundtrip(self):
        x = np.random.default_rng(1).standard_normal((8, 768), dtype=np.float32)
        y = quants.dequantize(ggml_quantize(x, T.Q6_K), T.Q6_K)
        self.assertLess(np.sqrt(np.mean((x - y) ** 2) / np.mean(x**2)), 0.02)

    def test_targets(self):
        hits = ["blk.0.hc_attn_down.weight", "blk.47.hc_attn_up.weight", "blk.3.hc_attn_inject.weight",
                "blk.0.hc_ffn_down.weight", "blk.0.hc_ffn_up.weight", "blk.0.hc_ffn_inject.weight",
                "output_hc_down.weight", "output_hc_up.weight", "blk.48.nextn.hc_head_down.weight",
                "blk.48.nextn.hc_head_up.weight"]
        misses = ["blk.0.hc_attn_norm.weight", "output_hc_norm.weight", "blk.48.nextn.hc_head_norm.weight",
                  "blk.0.ffn_gate_inp_shexp.weight", "blk.0.ffn_gate_exps.weight", "output.weight",
                  "blk.3.indexer.q_proj.weight", "blk.0.ssm_alpha.weight", "blk.1.ple_value.weight"]
        router = "blk.5.ffn_gate_inp.weight"
        self.assertEqual([n for n in hits if not HC.search(n) or ROUTER.search(n)], [])
        self.assertEqual([n for n in misses if HC.search(n) or ROUTER.search(n)], [])
        self.assertTrue(ROUTER.search(router) and not HC.search(router))


if __name__ == "__main__":
    unittest.main()
