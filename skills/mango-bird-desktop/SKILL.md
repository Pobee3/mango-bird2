---
name: mango-bird-desktop
description: Install, build, configure, or troubleshoot the Mango Bird macOS desktop pet from its GitHub repository or local checkout. Use when the user wants Codex or Claude Code to turn Mango Bird into a runnable macOS desktop pet, install the bundled app, configure their own model service API key for the chat panel, or explain how to publish/install the Mango Bird skill from GitHub.
---

# Mango Bird Desktop

## Overview

Mango Bird is a macOS desktop pet built from the `mango-bird` web prototype. The app uses a tiny native Swift `WKWebView` shell, starts the local Python server, reads the user's own model service API key from a local `.env`, and loads `mango-bird.html?desktop=1`.

Never ask the user to put API keys in repository files. Configure keys only in the user's local environment or in:

```text
~/Library/Application Support/Mango Bird/.env
```

## Install Workflow

1. Locate the Mango Bird project root. It is the folder containing `mango-bird.html`, `mango-bird-server.py`, and `macos/build-mango-bird-app.sh`.
2. On macOS, install with the bundled script:

```bash
python3 skills/mango-bird-desktop/scripts/install_mango_bird.py
```

3. If the user provides an API key, pass it only as a local install-time argument. Supported providers are `deepseek` and `glm`:

```bash
python3 skills/mango-bird-desktop/scripts/install_mango_bird.py --provider glm --api-key "sk-..."
```

4. If the user does not provide a key, tell them to create:

```text
~/Library/Application Support/Mango Bird/.env
```

with:

```bash
MANGO_AI_PROVIDER=deepseek
MANGO_AI_API_KEY=sk-their-own-api-key
```

They can also launch the desktop app, open the chat panel, choose a provider, paste the API key into the chat input, and click send to save it locally.
API keys must be single-line values. If a provider's default model is unavailable, users may add `MANGO_AI_MODEL=...` to the same `.env`.

5. The app installs by default to:

```text
~/Applications/mango-bird.app
```

The script also leaves a build artifact at:

```text
dist/mango-bird.app
```

For CI or sandboxed validation, use `--config-dir /path/to/temp/config` so the script does not write to the real Application Support folder.

## Build Without Installing

Run:

```bash
bash macos/build-mango-bird-app.sh
```

Use this when the user only wants an app bundle for packaging, manual testing, or GitHub release assets.

## Runtime Notes

- The app requires macOS with Swift/AppKit/WebKit available and `/usr/bin/python3`.
- Windows, Linux, and other non-macOS systems can read this skill and repository, but cannot build or run the desktop pet app directly.
- Release ZIPs produced by the local build are not signed or notarized unless a separate signing step is performed. For small tests, tell users to unzip `mango-bird.zip`, avoid double-clicking first, right-click `mango-bird.app`, choose Open, then click Open again in the dialog.
- The Swift shell reads `~/Library/Application Support/Mango Bird/.env` and forwards `MANGO_AI_PROVIDER` and `MANGO_AI_API_KEY` to `mango-bird-server.py`. The legacy `DEEPSEEK_API_KEY` name remains supported for older installs.
- Without a key, the desktop pet still runs; only the chat panel reports that an API key is not configured.
- The server binds to `127.0.0.1` on an automatically chosen port and is terminated when the app exits.
- The transparent desktop window polls the web page's `isMangoPointerInteractive(x, y)` function to let clicks pass through outside Mango Bird UI.

## GitHub Distribution

For Codex users, keep this folder in the repo at:

```text
skills/mango-bird-desktop/
```

They can copy or install that folder into `~/.codex/skills/mango-bird-desktop`, then ask Codex to use `$mango-bird-desktop`.

For Claude Code users, the same folder works as a portable agent instruction bundle: point Claude Code at `skills/mango-bird-desktop/SKILL.md` and ask it to run the install workflow from the repository checkout.

## Troubleshooting

- If the app opens but chat fails, check `~/Library/Application Support/Mango Bird/.env` for `MANGO_AI_PROVIDER` and `MANGO_AI_API_KEY`.
- If building fails, run `swift --version` and confirm the macOS command line tools are installed.
- If the app starts but no bird appears, run `python3 mango-bird-server.py` from the project root and open the printed URL in a browser to isolate server versus app-shell issues.
- Do not commit `.env`, API keys, or user-specific app bundles.
