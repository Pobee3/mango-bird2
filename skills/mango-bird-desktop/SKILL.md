---
name: mango-bird-desktop
description: Install, configure, or troubleshoot the Mango Bird macOS desktop pet from the public Mango Bird skill distribution. Use when the user wants Codex or Claude Code to download the prebuilt macOS app, install it as a runnable desktop pet, configure their own model service API key for the chat panel, or explain how to install the Mango Bird skill from GitHub.
---

# Mango Bird Desktop

## Overview

Mango Bird is a macOS desktop pet distributed as a prebuilt app ZIP plus this Codex skill. The app uses a tiny native Swift `WKWebView` shell, runs a Swift local HTTP/API server, reads the user's own model service API key from a local `.env`, and loads the bundled desktop page.

This skill is intentionally macOS-only. Keep the native Swift/WebKit app path; do not create an Electron, browser-only, Windows, or Linux fallback.

Never ask the user to put API keys in repository files. Configure keys only in the user's local environment or in:

```text
~/Library/Application Support/Mango Bird/.env
```

## Install Workflow

When the user asks "使用 $mango-bird-desktop 安装 Mango Bird macOS 桌宠", run the install workflow for them. Do not tell ordinary users to run scripts manually unless they explicitly want terminal commands.

1. Confirm the user is on macOS. Running the downloaded app does not require Python, Xcode, or Electron. Codex uses this Python installer only as an installation helper.
2. Run the bundled installer from the skill. In normal public installs, it downloads the prebuilt app ZIP from the GitHub release and copies `mango-bird.app` to `~/Applications`.

```bash
python3 /path/to/mango-bird-desktop/scripts/install_mango_bird.py
```

Use `--app-zip-url` only when testing a different release asset. Developers with a full source checkout can pass `--source-dir /path/to/mango-bird` or `--build-from-source`; source builds require Swift/AppKit/WebKit from Xcode or the macOS Command Line Tools.

3. If the user provides an API key, pass it only as a local install-time argument. Supported providers are `deepseek` and `glm`:

```bash
python3 /path/to/mango-bird-desktop/scripts/install_mango_bird.py --provider glm --api-key "your-api-key"
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

For CI or sandboxed validation, use `--config-dir /path/to/temp/config` so the script does not write to the real Application Support folder.

## Build Without Installing

Run:

```bash
bash macos/build-mango-bird-app.sh
```

Use this when the user only wants an app bundle for packaging, manual testing, or GitHub release assets.

## Runtime Notes

- The downloaded app requires macOS and does not require Python, Xcode, or Electron at runtime.
- The public repository does not need to expose source artwork as loose files; the release ZIP must include all runtime resources inside `mango-bird.app`.
- Building from source is a developer-only path and requires Swift/AppKit/WebKit through Xcode or the macOS Command Line Tools.
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
- If the app download fails, check that the GitHub release includes `mango-bird.zip`.
- If a developer source build fails, run `swift --version` and confirm the macOS Command Line Tools are installed. If they are missing, tell the user to run `xcode-select --install` in Terminal, complete the installer, then retry.
- If the app starts but no bird appears, the release ZIP is incomplete; rebuild the app and check that `mango-bird.html`, `assets/`, and `new2/` were copied into `mango-bird.app/Contents/Resources/MangoBird/`.
- Do not commit `.env`, API keys, or user-specific app bundles.
