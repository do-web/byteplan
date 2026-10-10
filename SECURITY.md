# Security

Byteplan runs a local server on `127.0.0.1:8080`. It is meant for your own Mac only.

- Do not expose the port to a network. `--agent` lets the model read and write files and run shell commands as your user.
- `bin/run` downloads only weight, config and tokenizer files (`.gguf`, `.safetensors`, `.json`, tokenizer files). It never runs code from a model repository.

Found a security problem? Please open a private report via GitHub (Security tab, "Report a vulnerability") instead of a public issue.
