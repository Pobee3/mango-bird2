# Mango Bird

mango-bird macOS 桌宠：可摸头、查看天气、临时问 AI 问题和设置待办事项提醒。

这个公开仓库主要服务两类用户：

- 普通用户：让 Codex 安装 skill，并自动下载已经打包好的 macOS app。
- 开发者：阅读 skill、Swift 桌面壳、网页互动逻辑和开发说明，学习这个桌宠是怎么实现的。

完整开发说明请优先读取 [docs/development.md](docs/development.md)。

普通网页版互动入口已取消。直接打开 `mango-bird.html` 时只会显示桌面版提示；桌面壳会加载桌面模式页面。

## 快速安装

如果你从未使用过这个项目，先把这个 GitHub skill 地址发给 Codex，请它安装：

```text
https://github.com/Pobee3/mango-bird2/tree/main/skills/mango-bird-desktop
```

更稳的流程是让 Codex 负责下载和安装，你自己负责启动。这样不会因为 Codex 要控制 `System Events` 而弹 macOS 自动化权限。可以直接复制这段话给 Codex：

```text
请从这个 GitHub 地址安装 Mango Bird skill：
https://github.com/Pobee3/mango-bird2/tree/main/skills/mango-bird-desktop

安装完成后，使用 $mango-bird-desktop 安装 Mango Bird macOS 桌宠。
```

安装 skill 后重启 Codex，然后直接对 Codex 说：

```text
使用 $mango-bird-desktop 安装 Mango Bird macOS 桌宠
```

Codex 会运行 skill 安装器，下载 GitHub Release 里的 `mango-bird.zip`，并把 app 安装到：

```text
~/Applications/mango-bird.app
```

安装完成后，在终端里自己打开：

```bash
open "$HOME/Applications/mango-bird.app"
```

如果 macOS 拦截未签名 app，再执行：

```bash
xattr -dr com.apple.quarantine "$HOME/Applications/mango-bird.app"
open "$HOME/Applications/mango-bird.app"
```

## macOS 桌宠应用

本项目包含原生 macOS 轻量封装，不需要 Electron。当前桌面版只支持 macOS；Windows、Linux 或其他非 macOS 电脑可以下载仓库阅读 skill 和开发说明，但不能直接运行这个桌面 app。

当前 app 已改为 Swift 原生本地代理。直接下载 app 的用户不需要额外安装 Python runtime，也不需要 Xcode 或 Command Line Tools 才能运行。

未签名、未公证的 app 在其他 Mac 上首次打开时可能被 Gatekeeper 拦截。小范围测试时可以这样打开：

1. 解压 `mango-bird.zip`
2. 不要直接双击
3. 右键 `mango-bird.app`
4. 选择“打开”
5. 弹窗里再次点“打开”

面向正式发布时，建议使用 Apple Developer ID 签名并 notarize。

## API Key

桌面应用会读取用户本机配置：

```text
~/Library/Application Support/Mango Bird/.env
```

聊天功能需要每个用户配置自己的模型服务 API Key。桌面版可直接在聊天输入框保存；也可以手动写入：

```text
MANGO_AI_PROVIDER=deepseek
MANGO_AI_API_KEY=your-api-key
```

支持 `deepseek` 和 `glm`。如果不配置 Key，桌宠仍可运行，只有“问小鸟”聊天会提示缺少 Key。不要把 `.env` 或 API Key 提交到 GitHub。

默认模型会随服务商选择：DeepSeek 使用 `deepseek-v4-flash`，GLM 使用 `glm-4-flash`。页面内不显示模型与模式切换按钮。

如果服务商提示模型不可用，可在 `.env` 中手动覆盖：

```text
MANGO_AI_MODEL=你的可用模型名
```

API Key 应保持为单行文本，不要包含换行。

## 本地开发

公开仓库保留了主要实现文件，适合学习桌宠结构和 skill 安装流程。因为运行素材不以散文件形式全部放在仓库里，普通用户应通过 Release app 安装；完整源码构建需要包含运行素材的本地开发目录。

开发者如果在完整源码目录中，可以构建桌面 app：

```bash
bash macos/build-mango-bird-app.sh
open "dist/mango-bird.app"
```

旧的 Python 聊天服务仍保留为开发排查参考，但当前发布 app 已使用 Swift 原生本地代理：

```bash
export MANGO_AI_PROVIDER="deepseek"   # deepseek / glm
export MANGO_AI_API_KEY="你的 API Key"
python3 mango-bird-server.py
```

## Skill

Codex 用户可以从公开仓库安装：

```text
https://github.com/Pobee3/mango-bird2/tree/main/skills/mango-bird-desktop
```

安装后使用：

```text
使用 $mango-bird-desktop 安装 Mango Bird macOS 桌宠
```

Claude Code 用户也可以直接读取同一份 `skills/mango-bird-desktop/SKILL.md`，让它按 install workflow 执行安装。

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
- 睡着后，单击或双击小鸟会唤醒，并播放抖擞动画。

## 文件

- `README.md`：面向普通用户和开发者的项目入口说明。
- `docs/development.md`：架构、功能映射、状态机和开发说明。
- `mango-bird.html`：桌面壳加载的互动页面，普通网页版入口已禁用。
- `macos/`：macOS 桌面应用 Swift 壳与构建脚本。
- `skills/mango-bird-desktop/`：可随 GitHub 发布、供 Codex 或 Claude Code 执行安装与配置的 skill。
- `mango-bird-server.py`：旧 Python 聊天服务，保留为开发排查参考。
- `time_parser.py` 与 `tests/test_time_parser.py`：自然语言提醒解析器及测试。

运行所需图片资源已封装在 Release 的 `mango-bird.zip` 内。想溯源素材的开发者可以下载 release app，并打开：

```text
mango-bird.app/Contents/Resources/MangoBird/
```
