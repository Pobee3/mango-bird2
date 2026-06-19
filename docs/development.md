# Mango Bird Development Notes

This public distribution is optimized for installing the Codex skill and the prebuilt macOS app. It also keeps the main implementation files readable for people who want to learn how the desktop pet works.

## Architecture

- `skills/mango-bird-desktop/` contains the Codex skill and installer.
- `macos/MangoBirdApp.swift` is the native macOS shell. It creates the transparent desktop window, hosts `WKWebView`, and runs a local Swift HTTP/API server on `127.0.0.1`.
- `mango-bird.html` is the interactive pet UI loaded by the app with desktop mode enabled.
- `time_parser.py` and `tests/` contain the natural-language reminder parser and its tests.
- `mango-bird-server.py` is the older Python development server, kept as a reference path for local debugging.

## Runtime Assets

The app needs image assets to look and behave like the packaged Mango Bird. For public installs, these assets are bundled inside the GitHub release ZIP:

```text
mango-bird.app/Contents/Resources/MangoBird/
```

That means normal users do not need loose source artwork in the repository. They install the skill, and the skill downloads the release app ZIP.

Developers who want to inspect the exact runtime resources can download the release ZIP and open the `.app` bundle:

```text
mango-bird.app/Contents/Resources/MangoBird/assets/
mango-bird.app/Contents/Resources/MangoBird/new2/
```

## Source Build

Source builds are developer-only. They require macOS plus Xcode or the macOS Command Line Tools:

```text
xcode-select --install
```

When a full source checkout includes runtime assets, build with:

```bash
bash macos/build-mango-bird-app.sh
```

The output app appears at:

```text
dist/mango-bird.app
```

## API Keys

Never commit API keys. Mango Bird reads user-local configuration from:

```text
~/Library/Application Support/Mango Bird/.env
```

Supported providers are `deepseek` and `glm`.
