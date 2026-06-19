# Mango Bird

完整项目上下文、当前实现、素材映射与后续开发约定请优先读取
[`AGENTS.md`](AGENTS.md)。

mango-bird macOS 桌宠：可摸头、查看天气、临时问 AI 问题和设置待办事项提醒。

## 本地开发

聊天服务可在项目目录中单独启动，用于排查桌面 app 内置服务：

```bash
cd mango-bird
export MANGO_AI_PROVIDER="deepseek"   # deepseek / glm
export MANGO_AI_API_KEY="你的 API Key"
python3 mango-bird-server.py
```

普通网页版互动入口已取消。直接打开 `mango-bird.html` 时只会显示桌面版提示；桌面壳会加载 `mango-bird.html?desktop=1`。

## macOS 桌宠应用

本项目包含原生 macOS 轻量封装，不需要 Electron。当前桌面版只支持 macOS；Windows、Linux 或其他非 macOS 电脑可以下载源码和 skill 阅读安装说明，但不能直接运行这个桌面 app。直接下载 app 的用户需要 macOS 自带或命令行工具提供的 `/usr/bin/python3`：

```bash
cd mango-bird
bash macos/build-mango-bird-app.sh
open "dist/mango-bird.app"
```

也可以用随仓库发布的 skill 安装到 `~/Applications`：

```bash
cd mango-bird
python3 skills/mango-bird-desktop/scripts/install_mango_bird.py
```

桌面应用会读取用户本机配置：

```text
~/Library/Application Support/Mango Bird/.env
```

聊天功能需要每个用户配置自己的模型服务 API Key。桌面版可直接在聊天输入框保存；也可以手动写入：

```bash
MANGO_AI_PROVIDER=deepseek
MANGO_AI_API_KEY=你的 API Key
```

支持 `deepseek` 和 `glm`。如果不配置 Key，桌宠仍可运行，只有“问小鸟”聊天会提示缺少 Key。不要把 `.env` 或 API Key 提交到 GitHub。

Codex 用户可以把 `skills/mango-bird-desktop/` 安装到 `~/.codex/skills/`，然后让 Codex 使用 `$mango-bird-desktop` 安装或排查。Claude Code 用户也可以直接读取同一份 `skills/mango-bird-desktop/SKILL.md` 执行安装流程。

默认模型会随服务商选择：DeepSeek 使用 `deepseek-v4-flash`，GLM 使用 `glm-4-flash`。页面内不显示模型与模式切换按钮。

如果服务商提示模型不可用，可在 `.env` 中手动覆盖：

```bash
MANGO_AI_MODEL=你的可用模型名
```

API Key 应保持为单行文本，不要包含换行。

## 分发说明

`dist/mango-bird.zip` 可用于本地测试分发。未签名、未公证的 app 在其他 Mac 上首次打开时可能被 Gatekeeper 拦截。小范围测试时可以这样打开：

1. 解压 `mango-bird.zip`
2. 不要直接双击
3. 右键 `mango-bird.app`
4. 选择“打开”
5. 弹窗里再次点“打开”

面向正式发布时，建议使用 Apple Developer ID 签名并 notarize。

直接下载 app 的用户还需要系统可用的 `/usr/bin/python3`。如果对“下载即用”要求更高，后续应把 Python 运行时打包进 app，或把本地代理改成 Swift 原生实现。

## 互动

- 点击芒果后，小鸟跳出。
- 每天本地时间早上 6 点，如果页面或桌面应用保持运行，小鸟会自动回到芒果状态；点击芒果后代表新一天重新孵化。
- 右键点击鸟身会在小鸟右上角弹出淡蓝灰色小框，可选择“回巢”退出桌宠。
- 光标停在小鸟头上会触发蹭蹭。
- 单击小鸟会弹出高透明磨砂工具框；双击小鸟查看当前位置天气，右键天气泡泡会重新定位并刷新本地天气。工具框打开后，小鸟会缩小并跳到框的右上沿。
- macOS 桌面版中，小鸟尺寸略小；单击小鸟打开问答/计时工具框，双击小鸟查看天气，额外支持按住小鸟拖动位置。
- 工具框默认打开“问小鸟”，适合临时知识问答；聊天只保留最近 12 条消息，约等于 6 轮对话，超过后会丢弃最早消息，因此不适合长期记忆或连续项目上下文，刷新后也会清空。
- “计时提醒”页签保留原有番茄钟、自然语言提醒和待办功能。
- 选择计时后弹框关闭，小鸟返回原位；计时完成时不播放芒果变身或额外提醒动画。
- 番茄钟选项为 `25/5` 和 `50/10`，分别表示专注 25 分钟/休息 5 分钟、专注 50 分钟/休息 10 分钟；计时期间面板折叠为带发光进度与倒计时的单个按钮，完整周期结束后自动展开。
- 可输入自定义内容和日期时间，到点后在小鸟左上方显示文字提醒卡。
- 停止互动 4 秒后，小鸟会歪头并眨眼；再过 8 秒仍无互动则睡觉。

## 文件

- `mango-bird.html`：桌面壳加载的互动页面，普通网页版入口已禁用。
- `macos/`：macOS 桌面应用 Swift 壳与构建脚本。
- `skills/mango-bird-desktop/`：可随 GitHub 发布、供 Codex 或 Claude Code 执行安装与配置的 skill。
- `assets/芒果_nobg.png`：开场芒果。
- `assets/终图_绿翅.png`：小鸟默认形象。
- `assets/bird-frames/`：蹭蹭等历史动作帧素材。
- `new2/`：睡觉、抖擞和左右走动作的源图。
- `time_parser.py` 与 `tests/test_time_parser.py`：自然语言提醒解析器及测试。
