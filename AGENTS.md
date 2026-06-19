# Mango Bird 项目上下文与协作指引

> 处理本项目中的 Mango Bird 任务时，优先读取本文件，再按需查看源码和素材。
> 本文件记录的是当前 Mango Bird 文件夹中的实际成果；若说明与代码不一致，以 `mango-bird.html` 为准，并同步更新本文档。

## 1. 项目概述

Mango Bird 是一个 macOS 桌面版 mango-bird 桌宠。用户点击芒果后，小鸟会从芒果中孵化出来，并通过逐帧 PNG、CSS 动画和 JavaScript 状态控制完成摸头蹭蹭、天气气泡、临时 AI 问答、待办事项提醒、待机眨眼、睡觉和唤醒等互动。

当前产品入口只保留 macOS 桌面版。核心 HTML、CSS 和 JavaScript 仍位于 `mango-bird.html`，但普通网页打开时只显示桌面版提示，不再提供网页版互动。Windows、Linux 或其他非 macOS 电脑可以下载源码和 skill 阅读安装说明，但不能直接运行这个桌面 app。桌面 app 的本地静态服务、配置保存和 DeepSeek/GLM 代理由 Swift 壳内置实现；`mango-bird-server.py` 仅保留作开发对照和排查工具。

macOS 桌面版位于 `macos/`，使用原生 Swift `WKWebView` 透明置顶窗口加载 `mango-bird.html?desktop=1`，并启动 Swift 原生本地 HTTP/API 服务。随仓库发布的 `skills/mango-bird-desktop/` 可供 Codex 或 Claude Code 从 GitHub checkout 中安装、构建和配置用户自己的模型服务 API Key。
桌面模式会使用略小的小鸟和芒果尺寸，隐藏开场提示但保留小鸟阴影；单击小鸟打开问答/计时工具框，双击小鸟显示天气，右键鸟身显示回巢，右键天气泡泡刷新当地天气，额外支持按住小鸟拖动位置。透明区域保持点击穿透。桌面尺寸下摸头热区、天气泡泡、天气点击热区、提醒弹框和提醒文字按实际渲染宽度缩放。

## 2. 当前入口

- 主页面：`mango-bird.html`（仅供桌面壳以 `?desktop=1` 加载）
- 开发对照服务：`mango-bird-server.py`
- macOS 桌宠构建脚本：`macos/build-mango-bird-app.sh`
- macOS 桌宠 Swift 壳：`macos/MangoBirdApp.swift`
- 安装配置 skill：`skills/mango-bird-desktop/SKILL.md`
- 项目简要说明：`README.md`
- 默认小鸟形象：`assets/终图_绿翅.png`
- 开场芒果：`assets/芒果_nobg.png`
- Mango Bird 动作帧：`assets/bird-frames/`
- 动作帧生成提示词：`assets/bird-frames/prompts.md`

普通网页版互动入口已取消；直接访问 `mango-bird.html` 只显示桌面版提示。天气功能需要联网，并会优先调用 WebKit 定位权限显示当前位置天气。若定位不可用或被拒绝，才使用上海作为后备坐标。

AI 聊天需设置个人模型服务 Key 并改用本地服务启动：

```bash
cd mango-bird
export MANGO_AI_PROVIDER="deepseek"  # deepseek / glm
export MANGO_AI_API_KEY="你的 API Key"
python3 mango-bird-server.py
```

Key 只从环境变量读取，不写入 HTML、浏览器存储或项目文件。
macOS 桌面应用还会读取用户本机的 `~/Library/Application Support/Mango Bird/.env`，用于启动时传入 `MANGO_AI_PROVIDER` 和 `MANGO_AI_API_KEY`。不要把 `.env` 或 API Key 提交进仓库。
默认模型随服务商选择：DeepSeek 使用 `deepseek-v4-flash`，GLM 使用 `glm-4-flash`。聊天页不显示模型与模式切换控件。

## 3. 已实现互动

### 孵化

1. 初始页面中央显示会呼吸浮动的芒果。
2. 点击芒果后，芒果左右摇晃 4 次。
3. 芒果放大消失，同时生成 35 个星光粒子。
4. 小鸟从中央缩放弹出，约 820 毫秒后进入 `idle`。
5. 页面保持运行时，每天本地时间早上 6 点会自动执行 `resetAll()` 回到芒果状态；用户点击芒果后再孵化为小鸟，作为新一天开始的仪式。
6. 右键点击鸟身会在小鸟右上角显示淡蓝灰色圆角弹出框；选择“回巢”会通过 `window.webkit.messageHandlers.mangoDesktop` 通知原生壳退出应用。右键天气泡泡刷新当地天气，不打开回巢菜单。

### 摸头蹭蹭

- 光标进入小鸟头部椭圆热区并停留 500 毫秒后触发。
- 使用 `nuzzle-01.png` 至 `nuzzle-04.png`。
- 每帧 140 毫秒，播放约 3 轮后回到待机。
- 光标离开头部区域后才会重新允许下一次蹭蹭，避免连续误触。

### 天气气泡

- 双击小鸟会吐出显示天气图标和当前温度的圆形气泡；单击则打开聊天与计时工具框。
- 首次点击芒果时会提前加载天气。
- 天气读取 Open-Meteo 的当前天气码和当前温度，不再使用全天汇总天气码。
- 天气结果缓存 2 分钟，超过时间后再次点击小鸟会自动刷新，以便外出移动后更快跟随当前位置变化。
- 打开聊天或计时面板时，正在显示或等待显示的天气气泡会立即静默隐藏，不播放破裂动画。
- 浏览器定位启用高精度，坐标最多复用 1 分钟。
- 右键点击正在显示的天气气泡会强制跳过天气缓存和定位缓存，重新请求浏览器当前位置并刷新本地天气；这不会打开“回巢”右键菜单。
- 优先请求浏览器当前位置；失败时使用上海后备坐标：

```text
纬度 31.2304，经度 121.4737
```

- 天气数据来自 Open-Meteo：

```text
https://api.open-meteo.com/v1/forecast
```

- 支持晴、多云、阴、雾、毛毛雨、雨、雪和雷暴图标。
- 点击天气气泡可使其破裂；右键天气气泡可重新定位并刷新；不操作时显示 5 秒后自动消失。

### 番茄钟与待办事项提醒

- 单击小鸟会在小鸟附近打开高透明磨砂工具框，默认显示“问小鸟”，也可切换到“计时提醒”。为区分双击天气，面板会在约 260 毫秒后打开。桌面模式保持同一套点击语义，并额外支持按住小鸟拖动位置。小鸟缩小后沿弧线跳到框内的右上区域，身体向面板内侧收进，双脚明确落在面板内部，面朝左侧静止站立；停驻时不显示地面阴影，也不沿用待机悬浮效果。
- 小鸟停驻在面板右上角时，位置和双脚保持固定，并以约 4.8 秒一轮的轻微身体伸缩呈现缓慢呼吸感；缓慢眨眼和以脚底为支点的轻微歪头各自约每 20 秒触发一次。
- 面板出现后，可按住标题或面板空白区域拖动整体位置；按钮、输入框等控件仍保持原有操作，小鸟会跟随面板并始终站在右上角。
- 计时面板折叠后，当前计时按钮只用于暂停或继续，不负责拖动；需要移动折叠面板时按住小鸟拖动。
- 小鸟站在工具框右上角时，也可按住小鸟拖动整个面板；短按小鸟仍保留关闭或展开/折叠计时菜单的行为。
- 计时框不显示关闭按钮；再次点击站在框上的小鸟会收起框，并恢复小鸟打开前的位置、大小和朝向。
- 番茄钟提供两个正式周期按钮：`25/5` 表示专注 25 分钟、休息 5 分钟；`50/10` 表示专注 50 分钟、休息 10 分钟。
- 选择周期后完整面板折叠，只保留所选按钮；按钮显示 `⌛️` 与当前阶段倒计时，并以淡青发光填充从左到右显示进度。
- 折叠后的计时按钮宽约 112px；点击活动按钮会暂停倒计时和进度，并在右侧显示“继续”“取消”。
- “继续”会从冻结点续跑并顺延周期；“取消”会清除当前周期并恢复完整菜单。
- 计时期间单击右上角小鸟可在完整菜单与“小鸟 + 单独计时器”的折叠界面之间切换；活动按钮仍显示原有倒计时、进度和暂停操作。
- 折叠计时器会显示“专注中”“休息中”或“已暂停”阶段文字；专注结束后的 5 秒提示等待期不显示阶段文字，正式开始休息倒计时后才显示“休息中”。
- 专注阶段结束后同一按钮自动进入休息倒计时；休息结束才恢复完整面板，可再次点击对应按钮开始下一轮。
- 专注阶段结束后，小鸟会先冒出“该休息啦～”并停留 5 秒；提示期结束后才从完整休息时长开始倒计时。
- 选择番茄钟后计时框关闭，小鸟返回打开前的位置；番茄钟不再使用芒果变身、发光轮廓或倒计时视觉。
- 专注完成后静默结束，不再弹出水杯、伸懒腰、休息提示或连续专注提示，也不再触发 3 小时跳跃提醒。
- `⏰ 提醒我` 标题与番茄钟标题字号一致；输入提醒后按回车添加，不显示独立“添加”按钮。
- 提醒输入框默认占满菜单内容宽度，使用与主色系协调但更轻的雾薄荷底色和灰青边框；示例文字靠左且垂直居中，不显示尺寸拖拽控件。
- 待办卡片与输入框等宽，前方勾选框略小于事项文字；事项标题会剥离日期、时刻和“提醒我”，具体触发时间显示在下方时间行。
- 中文时间解析支持月日、本月、今天、明天、明早、后天、本周/这周/下周、几点几分、冒号时刻、半小时后、X 小时 X 分钟后和中文/阿拉伯数字混合组合；`h` 可代替“小时”，`min` 可代替“分钟”，中文数字兼容常用写法与财务大写。
- 检测到未来时间时加入站内提醒队列，并以净化后的事件名生成标准 `.ics` 日历事件供系统日历导入；无时间内容清理“提醒我”等提示词后作为普通待办。
- 自定义提醒到点后使用短小提示语，不使用容易造成换行的长前后缀；包含“喝水”“饮水”或“补水”的事项固定显示“啾～该喝水啦”，其他事项在“该…啦～”“…时间到啦～”“啾～该…啦”中随机选择。部分站内提醒会随机附加一个轻量表情，并非每条都有；气泡显示 5 秒后淡出，待办标题、日历标题和系统通知仍保留清晰的原事件名。
- 任何站内文字提醒弹出前，如果小鸟正处于 `sleeping`，会先播放 `waking` 抖擞动作，再显示提醒文字。
- 添加待办后输入框会立即清空并重新获得焦点，可连续录入；待办卡片上下高度约为上一版的四分之三。
- 待办区域可容纳并滚动查看至少 10 条紧凑卡片，避免列表增长时撑出菜单面板。
- 番茄钟、自定义提醒可同时存在，左上角倒计时徽标始终显示下一条提醒。
- 专注完成后左上角会显示“再次计时”徽标，点击可按上一次选项再次计时。
- 页面始终提供站内提醒；若浏览器通知权限已允许，也会同时发送桌面通知。

### 临时 AI 问答

- 小鸟名为 Mango。单击小鸟打开工具框后，默认进入“问小鸟”页签。
- 对话标题使用 `assets/mango-chat-avatar.png` 中带树枝、透明背景的黄色水墨小鸟头像，标题文字为“有什么想问的？”。
- 使用 DeepSeek 或 GLM 完成临时知识问答，默认使用中文、简洁且可靠地回答。
- Mango 的普通知识回答默认不使用表情，仅在鼓励、安慰、庆祝或轻松闲聊等合适场景偶尔使用一个，避免每轮固定或连续重复。
- 聊天页不提供模型与模式切换控件；前端只发送消息与快速模式，后端按 `MANGO_AI_PROVIDER` 选择默认模型。服务端仅在 DeepSeek 的 `thinking` 模式下发送 `thinking` 字段。
- 系统提示要求 Mango 使用自然纯文本回答，不使用 Markdown 加粗、标题、表格或代码块，尤其避免输出 `**`，除非用户明确要求格式化内容。
- Enter 发送，Shift+Enter 换行；请求期间显示“Mango 正在想…”。
- 只向模型携带当前页面最近 12 条消息，约等于 6 轮对话；超过后会丢弃最早消息，因此只适合临时问答，不适合长期记忆或连续项目上下文。
- 不使用 `localStorage`，重启桌面 app 会清空对话。
- “清空对话”会中止当前请求并立即清除当前会话。
- 缺少或无效的 API Key、网络超时和额度限制会在输入框下方显示错误。桌面版未配置时可在聊天面板选择 DeepSeek 或 GLM，并把 Key 输入到聊天框保存。

### 待机、睡觉与唤醒

- 每次回到 `idle` 后，停止互动 4 秒会播放 8 帧歪头眨眼。
- 歪头眨眼结束后，再停止互动 8 秒会进入睡觉。
- 睡觉使用 `sleep-01.png` 至 `sleep-03.png`，停留在最后一帧。
- 点击睡着的小鸟会播放 4 帧抖擞动作，然后回到待机。
- 抖擞使用 `ruffle-01.png` 至 `ruffle-04.png`。

### 重置

每日早上 6 点会自动回到芒果状态；右键鸟身选择“回巢”会退出应用。

## 4. 状态机

`pet.state` 当前可能使用以下状态：

| 状态 | 含义 | 主要进入方式 |
| --- | --- | --- |
| `hidden` | 小鸟未出现 | 页面初始化、重置 |
| `hatching` | 芒果摇晃或小鸟孵化中 | 点击芒果 |
| `idle` | 可正常互动的待机状态 | 孵化、动作结束、唤醒结束 |
| `nuzzle` | 摸头蹭蹭 | 光标在头部停留 |
| `dialogPerch` | 小鸟站在磨砂计时框右上沿 | 单击小鸟 |
| `headBlink` | 歪头眨眼 | 待机 4 秒 |
| `sleeping` | 睡觉 | 眨眼结束后再待机 8 秒 |
| `waking` | 抖擞唤醒 | 点击睡着的小鸟 |

`hidden`、`hatching`、`sleeping`、`waking` 和 `dialogPerch` 会阻止常规摸头等实时互动。

## 5. 动作素材映射

所有当前动作 PNG 均为 `1254 x 1254`、RGBA 透明背景，方便保持角色在不同动作间的尺寸和中心一致。

| 动作 | 代码中的帧组 | 当前接入素材 | 状态 |
| --- | --- | --- | --- |
| 默认待机 | 无 | `assets/终图_绿翅.png` | 已使用 |
| 蹭蹭 | `nuzzle` | `nuzzle-01` 至 `nuzzle-04` | 已使用 |
| 睡觉 | `sleeping` | `new2/sleep-01` 至 `sleep-03` | 已使用 |
| 抖擞 | `waking` | `new2/ruffle-01` 至 `ruffle-04` | 已使用 |
| 歪头眨眼 | `headBlink` | `head-blink-01` 至 `head-blink-08` | 已使用 |
| 向左走 | 无 | `new2/walk-left-01` 至 `walk-left-08` | 尚未接入 |
| 向右走 | 无 | `new2/walk-right-01` 至 `walk-right-08` | 尚未接入 |

注意：`hasFrameSet()` 至少检测到 2 张成功预加载的图片才会启用逐帧动画，否则自动使用默认图片和 CSS 动画。

## 6. 关键参数

参数集中在 `mango-bird.html` 的 `config` 对象中：

| 参数 | 当前值 | 作用 |
| --- | ---: | --- |
| `headNuzzleRadiusX` | `25` | 朝右时头部热区水平半径 |
| `leftHeadNuzzleRadiusX` | `32` | 朝左时头部热区水平半径 |
| `headNuzzleRadiusY` | `38` | 头部热区垂直半径 |
| `headOffsetX` | `54` | 朝右时头部中心水平偏移 |
| `leftHeadOffsetX` | `66` | 朝左时头部中心水平偏移 |
| `headOffsetY` | `-46` | 头部中心垂直偏移 |
| `nuzzleDwell` | `500 ms` | 悬停多久触发蹭蹭 |
| `nuzzleFrameDuration` | `140 ms` | 蹭蹭单帧时长 |
| `nuzzleLoops` | `3` | 蹭蹭循环轮数 |
| `hatchDuration` | `820 ms` | 孵化完成时间 |
| `screenPadding` | `72 px` | 小鸟距离屏幕边缘的基础留白 |
| `headBlinkIdleDelay` | `4000 ms` | 待机多久后歪头眨眼 |
| `sleepIdleDelay` | `8000 ms` | 眨眼后多久进入睡觉 |
| `singleClickDelay` | `260 ms` | 区分单击工具框与双击天气 |
| `sleepFrameDuration` | `420 ms` | 睡觉单帧时长 |
| `ruffleFrameDuration` | `240 ms` | 唤醒抖擞单帧时长 |

## 7. 代码结构

`mango-bird.html` 是单文件实现，按职责可分为：

- 页面与样式：舞台、芒果、小鸟、影子、提示文字、天气气泡、计时对话、提醒卡、粒子和重置按钮。
- 数据：`weatherVisuals`、`frameSets`、`config`、`pet`、`weather`、`reminderTimer`。
- 帧动画：`preloadFrameSet()`、`hasFrameSet()`、`playFrameSet()`。
- 状态控制：`setPetState()`、`returnToIdle()`、`beginPetInteraction()`。
- 角色动作：`startNuzzle()`、`playChaseAndPeck()`、`playPeck()`、`playHeadBlink()`、`enterSleep()`、`wakeFromSleep()`。
- 位置与命中检测：`clampPoint()`、`getBirdBodyMetrics()`、`getBirdHeadPoint()`、`isPointerInHeadZone()`。
- 天气：`requestBrowserLocation()`、`fetchTodayWeather()`、`loadTodayWeather()`、`spitWeatherBubble()`。
- AI 问答：`setDialogView()`、`renderChatMessages()`、`askBird()`、`clearChat()`。
- 计时与待办：`openTimerDialog()`、`startReminderTimer()`、`addCustomReminder()`、`scheduleNextReminder()`、`finishReminderTimer()`。
- 初始化与清理：`hatchFromMango()`、`spawnBird()`、`resetAll()`、`scheduleDailyMangoReset()`、`closeMangoPet()`。

页面还将部分调试和控制函数挂在 `window` 上，可在浏览器控制台直接调用：

```js
resetAll();
scheduleDailyMangoReset();
closeMangoPet();
playHeadBlink();
enterSleep();
wakeFromSleep();
returnToIdle();
loadTodayWeather();
openTimerDialog();
startReminderTimer({
  focusMs: 3000,
  restMs: 3000,
  focusMinutes: 30,
  restMinutes: 10
});
addCustomReminder('测试自定义提醒', Date.now() + 3000);
finishReminderTimer();
```

## 8. 视觉与交互约定

- 页面背景为暖白色 `#fdf6ee`。
- 聊天与计时工具框采用小鸟自身的浅青绿与柔和杏桃红橙配色：青绿作为通透主体，红橙用于顶部高光、边框和选中页签，不使用深色大面积填充。
- 开场芒果显示宽度为 `min(350px, 49vw)`。
- 小鸟显示宽度为 `clamp(150px, 22vw, 230px)`。
- 默认素材以朝右为基准，朝左主要依靠水平翻转。
- 小鸟位置使用中心坐标 `pet.x`、`pet.y`，CSS transform 负责渲染。
- 天气使用带高光及小圆泡尾的紧凑圆形泡泡，图标居中偏左上、温度贴近右下弧线；计时提醒和自定义提醒保持原来的圆角方框卡片样式。弹出内容整体位于小鸟左上方。
- 计时框根据小鸟位置动态布局，小鸟站位和计时芒果共用当前 `pet.x`、`pet.y`，因此变身与重新孵化发生在同一点。
- 所有移动目标会经过屏幕边界限制，避免角色跑出可视区域。
- 动作帧应保持透明背景、角色比例一致、主体居中且留白稳定。
- 生成新帧时继续使用 `assets/终图_绿翅.png` 作为唯一角色参考，以维持脸部颜色、喙、眼睛、翅膀和尾部特征一致。

## 9. 当前已知差异与待办

以下内容不是运行错误，而是当前成果中已经存在、后续开发时需要知道的差异：

1. `assets/bird-frames/chase-04.png` 和 `chase-05.png` 已存在，但 `frameSets.chase` 目前只接入前 3 帧。
2. 提示词文档设计过 `peck-01` 至 `peck-04`，但这些文件当前不存在，`frameSets` 中也没有 `peck`。
3. 左右走路各 8 帧已经准备好，但当前桌面版暂未接入走路动作。
4. 天气依赖网络、浏览器定位和 Open-Meteo；在直接使用 `file://` 打开页面或受限环境中可能无法正常请求。
5. 番茄钟、自定义提醒和每日 6 点芒果重置依赖页面持续打开；刷新或关闭页面会清除当前计时。
6. 当前工程已有 `tests/test_time_parser.py` 覆盖 Python 时间解析，但 `mango-bird.html` 中的浏览器交互和 JS 时间解析仍主要通过浏览器手动验证。

## 10. 后续修改原则

继续开发时建议遵循以下顺序：

1. 先读取本文件了解现状。
2. 再读取 `mango-bird.html` 中与目标功能相关的状态、事件和参数。
3. 修改动作时同时检查状态切换、计时器清理、帧预加载和默认图回退。
4. 新增逐帧素材时保持 `1254 x 1254` RGBA 透明 PNG，并更新 `frameSets`。
5. 修改实际行为、参数、入口或素材映射后，同步更新本文件。
6. 在桌面和窄屏尺寸下验证孵化、蹭蹭、天气、睡眠、唤醒、API 配置和重置完整流程。

## 11. 同工作区的相关成果

工作区中另有一套青羽小鸟成果，它不是 Mango Bird 主页面的一部分：

- `../qingyu-bird.js`：可复用的 `<qingyu-bird>` Web Component。
- `../qingyu-bird-demo.html`：组件演示页。
- `../assets/qingyu-widget/`：组件素材。
- `../runs/qingyu/`：完整的角色动画生成、拆帧、QA 和最终 spritesheet 产物。

这些文件可以作为后续组件化、精灵图制作和动画 QA 的参考，但不要在未明确需求时把青羽素材混入 Mango Bird。
