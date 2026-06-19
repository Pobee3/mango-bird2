# Mango Bird macOS Desktop Pet

Mango Bird is a macOS desktop pet distributed through a Codex skill. The public repository is mainly for users who want to install the skill and let Codex download and install the prebuilt app.

The desktop app is macOS-only. It uses a native Swift/WebKit shell and a Swift local API server, so the downloaded app does not require Electron, Xcode, or Python at runtime.

## Install With Codex

Ask Codex to install the skill from this GitHub path:

```text
https://github.com/Pobee3/mango-bird2/tree/main/skills/mango-bird-desktop
```

After Codex installs the skill, restart Codex and say:

```text
使用 $mango-bird-desktop 安装 Mango Bird macOS 桌宠
```

Codex will run the skill installer, download the latest `mango-bird.zip` release, and copy `mango-bird.app` to:

```text
~/Applications/mango-bird.app
```

## API Key

Each user should use their own model service API key. Do not put API keys in this repository.

The app stores local config here:

```text
~/Library/Application Support/Mango Bird/.env
```

The chat panel can save the key locally. Users who prefer manual config can write:

```text
MANGO_AI_PROVIDER=deepseek
MANGO_AI_API_KEY=your-api-key
```

Supported providers are `deepseek` and `glm`. Without an API key, the pet still runs; only the chat feature reports that a key is missing.

## Distribution Notes

The source artwork does not need to be published as loose files for users to run the pet. Runtime assets are bundled inside the release app ZIP.

The release app is unsigned unless a separate Apple Developer ID signing and notarization step is performed. For small tests, if macOS blocks the first launch, right-click `mango-bird.app`, choose Open, then confirm Open again.

## Skill Folder

The installable skill lives at:

```text
skills/mango-bird-desktop/
```

Claude Code users can also point Claude Code at `skills/mango-bird-desktop/SKILL.md` and ask it to follow the install workflow.
