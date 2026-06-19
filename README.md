# Mango Bird macOS Desktop Pet

Mango Bird is a macOS desktop pet distributed through a Codex skill. The public repository is mainly for users who want to install the skill and let Codex download and install the prebuilt app.

The desktop app is macOS-only. It uses a native Swift/WebKit shell and a Swift local API server, so the downloaded app does not require Electron, Xcode, or Python at runtime.

## What It Does

Mango Bird lives directly on the macOS desktop instead of inside a browser tab. It starts as a mango, then hatches into a small bird when clicked.

Interaction logic:

- The pet starts as a mango. Click the mango to make it shake, burst into small particles, and hatch the bird.
- After hatching, the bird idles on the desktop and turns toward the pointer.
- Drag the bird to move it around the desktop.
- Hover over the bird's head for a short moment to trigger the nuzzle animation.
- Click the bird once to open the translucent tool panel.
- When the tool panel is open, the bird perches on the panel edge. Click the bird again to close the panel.
- Double-click the bird to show a weather bubble.
- Click the weather bubble to pop it. Right-click the weather bubble to refresh location and reload weather.
- Right-click the bird body to show the return menu, then send it back to the mango.
- If the bird receives no interaction for about 4 seconds, it tilts/blinks as an idle reaction.
- If it receives no interaction for about 8 more seconds after that, it falls asleep.
- Click or double-click the sleeping bird to wake it up with a ruffle animation.
- Each day at local 6:00 AM, if the app is still running, the pet resets back to the mango state.

Tool panel features:

- Ask temporary AI questions in the chat panel.
- Save a DeepSeek or GLM API key locally from the chat panel.
- Use timer presets such as `25/5` and `50/10`.
- Create natural-language reminders and todo items.
- Show reminder cards near the bird when a reminder is due.

The pet still runs without an API key. Only the AI chat feature needs a key.

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
