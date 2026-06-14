# Mango Bird

完整项目上下文、当前实现、素材映射与后续开发约定请优先读取
[`AGENTS.md`](AGENTS.md)。

芒果小鸟桌宠互动原型：可摸头、冲刺啄、查看天气和设置健康提醒。

## 互动

- 点击芒果后，小鸟跳出。
- 光标停在小鸟头上会触发蹭蹭。
- 在小鸟外侧点击，小鸟会冲刺过去并啄光标。
- 单击小鸟查看天气；双击后会弹出淡青色高透明磨砂计时框，小鸟缩小并跳到框的右上沿。
- 选择计时后弹框关闭，小鸟返回原位；计时完成时不播放芒果变身或健康提醒动画。
- 番茄钟选项为 `30/5` 和 `60/10`；计时期间面板折叠为带发光进度与倒计时的单个按钮，完整周期结束后自动展开。
- 可输入自定义内容和日期时间，到点后在小鸟左上方显示文字提醒卡。
- 番茄钟启动满 3 小时后，小鸟会整体上下跳 3 次。
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
