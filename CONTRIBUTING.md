# Contributing

Bug reports and pull requests are welcome.

- **Speed changes must keep answers identical.** Show that the hashes in `tools/bench/proof.py` stay the same, before and after.
- Changes to llama.cpp go into `patches/` as a `git format-patch --zero-commit` series on the pinned commit (see `docs/PATCHES.md`).
- Shell scripts pass `shellcheck`, the guard tests pass: `bash bin/test-run-guarded.sh --no-smoke`.
- Bug reports: please include chip, memory, macOS version and the command you ran.
