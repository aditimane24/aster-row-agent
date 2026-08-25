Demo playback and GIF export

Files added:
- `deliverables/demo.cast` — asciinema v2 cast file recording a short terminal demo (pytest, deterministic eval, mock run, packaging).

Play the demo locally

1) Install `asciinema` (or use WSL on Windows):
- Ubuntu/Debian: `sudo apt install asciinema`
- macOS: `brew install asciinema`
- Windows: use WSL and install inside it, or install `asciinema-player` via `npm` for playback.

2) Play the cast:
```bash
asciinema play deliverables/demo.cast
```

Convert the cast to GIF

Option A — use Docker (recommended if you don't want to install ruby/node tools):
```bash
docker run --rm -v "%cd%":/data asciinema/asciicast2gif deliverables/demo.cast demo.gif
```

Option B — use `asciicast2gif`/other local converters (may require ruby/node/python tools). Search for `asciicast2gif` or `asciinema-to-gif` tools for your platform.

Notes

- The included cast is a short, deterministic replay of commands and outputs from this repository for reviewers to quickly inspect the flow.
- If you want a polished MP4/GIF I can generate one for you, but it requires a runtime conversion tool (Docker or a conversion utility) available on your machine; tell me if you want me to produce the GIF here and I'll attempt it with available tools.
