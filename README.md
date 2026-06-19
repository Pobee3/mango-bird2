# Mango Bird

完整项目上下文、当前实现、素材映射与后续开发约定请优先读取
[`AGENTS.md`](AGENTS.md)。

芒果小鸟桌宠互动原型：可摸头、冲刺啄、查看天气、临时问 AI 问题和设置健康提醒。

## 启动

普通互动仍可使用静态服务器启动：

```bash
python3 -m http.server 8000
```

若要使用“小鸟聊天”，先设置自己的 DeepSeek API Key，再启动本地服务：

```bash
export DEEPSEEK_API_KEY="你的 API Key"
python3 mango-bird-server.py
```

访问 `http://127.0.0.1:8000/mango-bird.html`。Key 只由本地 Python
服务从环境变量读取，不会进入网页或聊天记录。

默认模型为 `deepseek-v4-flash`，并关闭 thinking 使用快速模式；快速模式请求不会向 DeepSeek 发送 `thinking` 字段。页面内不再显示模型与模式切换按钮。这个配置只影响 Mango Bird 本地服务，不影响你在其他软件里用同一个 API Key 选择 Pro 或 thinking。

## 互动

- 点击芒果后，小鸟跳出。
- 每天本地时间早上 6 点，如果页面或桌面应用保持运行，小鸟会自动回到芒果状态；点击芒果后代表新一天重新孵化。
- 右键点击页面或 Mango 会在小鸟右上角弹出淡蓝灰色小框，可选择“回巢”隐藏桌宠；当前原型中点击“再来一次”可重新显示，桌面版中可接入真正退出应用。
- 光标停在小鸟头上会触发蹭蹭。
- 在小鸟外侧点击，小鸟会冲刺过去并啄光标。
- 单击小鸟会弹出高透明磨砂工具框；双击小鸟查看当前位置天气，右键天气泡泡会重新定位并刷新本地天气。工具框打开后，小鸟会缩小并跳到框的右上沿。
- 工具框默认打开“问小鸟”，适合临时知识问答；只保留当前页面最近约 6 轮上下文，刷新后清空。
- “计时提醒”页签保留原有番茄钟、自然语言提醒和待办功能。
- 选择计时后弹框关闭，小鸟返回原位；计时完成时不播放芒果变身或健康提醒动画。
- 番茄钟选项为 `25/5` 和 `50/10`，分别表示专注 25 分钟/休息 5 分钟、专注 50 分钟/休息 10 分钟；计时期间面板折叠为带发光进度与倒计时的单个按钮，完整周期结束后自动展开。
- 可输入自定义内容和日期时间，到点后在小鸟左上方显示文字提醒卡。
- 停止互动 4 秒后，小鸟会歪头并眨眼；再过 8 秒仍无互动则睡觉。

## 文件

- `mango-bird.html`：单文件互动页面。
- `assets/芒果_nobg.png`：开场芒果。
- `assets/终图_绿翅.png`：小鸟默认形象。
- `assets/bird-frames/`：蹭蹭和冲刺动作帧。

## 青羽 HTML 组件

`qingyu-bird.js` 提供一个可复用的 Web Component，包含自动随机歪头眨眼和点击触发。

```html
<script src="qingyu-bird.js"></script>
<qingyu-bird size="220" interactive="true"></qingyu-bird>
```

也可以通过 JavaScript 主动触发：

```js
const bird = document.querySelector("qingyu-bird");
bird.headBlink();
bird.blink(); // 同样播放歪头眨眼组合
bird.resetPose();
bird.pause();
bird.play();
```

- `qingyu-bird-demo.html`：独立互动演示。
- `assets/qingyu-widget/qingyu-head-blink.webp`：八帧透明歪头眨眼动作条。
