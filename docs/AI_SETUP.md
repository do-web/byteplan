# Setup guide for AI assistants

You are helping a user install Byteplan on their Mac. Keep your messages short and plain; the user may not be technical.

1. **Check the Mac** and tell the user what you found:
   - `uname -m` must be `arm64` (Apple Silicon).
   - Memory: `sysctl -n hw.memsize` (bytes). 64 GB or more: normal setup. 48 to 63 GB: use `--spar`. Less: Qwen3.8-Flash-Next does not fit; offer `./install.sh --no-model` and `bin/run` with a smaller model.
   - Free disk: `df -g ~`. Setup needs 150 GB free (the expert pool for `--spar` fits in that, it is built after cleanup). If there is not enough, ask the user what to delete or where to store the models (`export BYTEPLAN_MODELS=/Volumes/Disk/byteplan-models`, an external SSD works but is slower to start).
2. **Tools**: `xcode-select -p` (else ask the user to run `xcode-select --install` and click Install), then `brew install git cmake node uv` (Homebrew from https://brew.sh if missing; its installer asks for the user's password, so let the user run it).
3. **Install**: `git clone https://github.com/do-web/byteplan && cd byteplan && ./install.sh` (add `--spar` for 48 to 63 GB). It runs 20 minutes to a few hours depending on the internet connection (70 GB download). If it stops, run it again; it resumes.
4. **Start**: `bin/chat` (48 to 63 GB: `bin/chat --spar 256`). Loading takes 1 to 3 minutes. Then the user opens http://127.0.0.1:8080.
5. **Connect apps** if the user asks: OpenAI-compatible base URL `http://127.0.0.1:8080/v1` (any key, any model name); Anthropic-compatible `ANTHROPIC_BASE_URL=http://127.0.0.1:8080`.

Rules:
- Do not add `--uncensored` unless the user asks for it.
- Keep the server on 127.0.0.1. Do not expose it to the network.
- Do not start two models at once; `bin/run-guarded` refuses it anyway.
- Problems: see "Something went wrong?" in README.md; the log is `install.log`.
