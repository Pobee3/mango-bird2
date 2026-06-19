---
name: mango-bird-desktop
description: Install, build, configure, or troubleshoot the Mango Bird macOS desktop pet from its GitHub repository or local checkout. Use when the user wants Codex or Claude Code to turn Mango Bird into a runnable macOS desktop pet, install the bundled app, configure their own model service API key for the chat panel, or explain how to publish/install the Mango Bird skill from GitHub.
---

# Mango Bird Desktop

## Overview

Mango Bird is a macOS desktop pet built from the `mango-bird` web prototype. The app uses a tiny native Swift `WKWebView` shell, runs a Swift local HTTP/API server, reads the user's own model service API key from a local `.env`, and loads `mango-bird.html?desktop=1`.

This skill is intentionally macOS-only. Keep the native Swift/WebKit app path; do not create an Electron, browser-only, Windows, or Linux fallback.

Never ask the user to put API keys in repository files. Configure keys only in the user's local environment or in:

```text
~/Library/Application Support/Mango Bird/.env
```

## Install Workflow

When the user asks "使用 $mango-bird-desktop 安装 Mango Bird macOS 桌宠", run the install workflow for them. Do not tell ordinary users to run scripts manually unless they explicitly want terminal commands.

1. Confirm the user is on macOS. Building the app requires Swift/AppKit/WebKit from the macOS Command Line Tools or Xcode. Running the built app does not require Python.
2. Run the bundled installer from the skill. The installer automatically uses an existing project checkout when it is inside one; otherwise it clones the default GitHub repository first.

```bash
python3 /path/to/mango-bird-desktop/scripts/install_mango_bird.py
```

Use `--source-dir /path/to/mango-bird` to build from an existing checkout, `--repo-url` to override the source repository, and `--update-source` when the user wants to pull the latest GitHub version before building.

3. If the user provides an API key, pass it only as a local install-time argument. Supported providers are `deepseek` and `glm`:

```bash
python3 /path/to/mango-bird-desktop/scripts/install_mango_bird.py --provider glm --api-key "sk-..."
```

4. If the user does not provide a key, tell them to create:

```text
~/Library/Application Support/Mango Bird/.env
```

with:

```bash
MANGO_AI_PROVIDER=deepseek
MANGO_AI_API_KEY=your-api-key
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

- The built app requires macOS and does not require Python. Building from source requires Swift/AppKit/WebKit through Xcode or the macOS Command Line Tools.
- Windows, Linux, and other non-macOS systems can read this skill and repository, but cannot build or run the desktop pet app directly.
- Release ZIPs produced by the local build are not signed or notarized unless a separate signing step is performed. For small tests, tell users to unzip `mango-bird.zip`, avoid double-clicking first, right-click `mango-bird.app`, choose Open, then click Open again in the dialog.
- The Swift shell reads `~/Library/Application Support/Mango Bird/.env` and uses `MANGO_AI_PROVIDER`, `MANGO_AI_API_KEY`, and optional model settings in its built-in local API server. The legacy `DEEPSEEK_API_KEY` name remains supported for older installs.
- Without a key, the desktop pet still runs; only the chat panel reports that an API key is not configured.
- The server binds to `127.0.0.1` on an automatically chosen port and is terminated when the app exits.
- The transparent desktop window polls the web page's `isMangoPointerInteractive(x, y)` function to let clicks pass through outside Mango Bird UI.

## GitHub Distribution

For Codex users, keep this folder in the repo at:

```text
skills/mango-bird-desktop/
```

For ordinary Codex users, do not show terminal commands. Tell them to ask Codex to install the skill from `https://github.com/Pobee3/mango-bird/tree/main/skills/mango-bird-desktop`; after Codex has the skill, they should run the desktop pet with this single recommended prompt:

```text
使用 $mango-bird-desktop 安装 Mango Bird macOS 桌宠
```

For Claude Code users, the same folder works as a portable agent instruction bundle: point Claude Code at `skills/mango-bird-desktop/SKILL.md`, provide the GitHub repo URL if needed, and ask it to run the install workflow.

## Troubleshooting

- If the app opens but chat fails, check `~/Library/Application Support/Mango Bird/.env` for `MANGO_AI_PROVIDER` and `MANGO_AI_API_KEY`.
- If building fails, run `swift --version` and confirm the macOS Command Line Tools are installed. If they are missing, tell the user to run `xcode-select --install` in Terminal, complete the installer, then retry.
- If the built app starts but no bird appears, rebuild the app and check that `mango-bird.html`, `assets/`, and `new2/` were copied into `mango-bird.app/Contents/Resources/MangoBird/`.
- Do not commit `.env`, API keys, or user-specific app bundles.
