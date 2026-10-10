# `--uncensored` (off by default)

Qwen3.8-Flash-Next sometimes refuses harmless requests. `--uncensored` removes that habit at run time: it subtracts one learned direction ("refusal") from the model's internal state in layers 4 to 44. The direction comes from [Cudecnik/Qwen3.8-Flash-Next-refusal-projection](https://huggingface.co/Cudecnik/Qwen3.8-Flash-Next-refusal-projection) (480 KB). The model files on disk stay unchanged; without the flag nothing is applied.

```sh
./install.sh --uncensored    # once: downloads the direction file
bin/chat --uncensored
```

- It changes the answers on purpose. The speed comparisons in the README are measured without it.
- The model will then also answer requests it should refuse. You are responsible for how you use it and for following the law and the [Qwen license](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/main/LICENSE).
- Patch: `patches/0001` (env `BYTEPLAN_REFUSAL_PROJ`, unset = off).
