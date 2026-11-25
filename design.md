---
version: alpha
name: plot18
description: PLOT18 手机端 AI 陪伴聊天的设计系统 —— 暖黑 Night Craft / 和纸 Japanese Minimal、单一琥珀或陶土强调、衬线标题、发丝线与一层玻璃。
---

# PLOT18 Design System

本文件是 PLOT18 视觉与手机端交互的单一真相源。它从 `darl-tv/design.md` 的 plot 工作区设计系统继承视觉语法，但把「桌面无限画布」换成「手机上的私密聊天」：信息密度更低、触控目标更大、情绪更安静。

品牌基准是 [plot18.com](https://www.plot18.com/) 的 Night Craft：暖黑底、琥珀金、衬线大标题、影院感。PLOT18 不复制它的页面结构，只把视觉语法用于「选她 → 和她说话」这条路径。

- **暗色 = Night Craft（默认）**：`#101114` 暖黑、`#E8A532` 琥珀、`#F3F0E8` 米白。
- **亮色 = Japanese Minimal**：`#F7F1E8` 和纸、`#B34631` 陶土红、`#302821` 墨色。
- 两套主题共用同一套语义令牌，亮色不是暗色反相。

代码落地位置：

- 颜色 / 字体 / 圆角 / 阴影：`frontend/src/styles/tokens.css`
- 基础组件、按钮、表单、抽屉、Toast、年龄门：`frontend/src/styles/base.css`
- 发现页、人设卡、详情抽屉：`frontend/src/styles/discover.css`
- 聊天页、气泡、工具卡、图片 / 语音、输入区：`frontend/src/styles/chat.css`
- 消息列表、我的、登录：`frontend/src/styles/pages.css`
- 后台：`frontend/src/styles/admin.css`

新增界面先在这里找到语义令牌，再去 `tokens.css` 取值。组件里不写死颜色。

## Overview

PLOT18 是一个「手机全屏 + 底部三栏 + 私密对话」的产品。界面必须退到人设和对话后面：

- **一个强调色**：暗色琥珀 `#E8A532`，亮色陶土 `#B34631`。只用于当前 / 选中 / 主操作 / 在线 / 亲密度，不做大面积装饰。危险操作单独用 `--danger`。
- **衬线只做标题**：品牌字标、页面主标题、区块标题、人设名、气泡外的关系数字用 Georgia / 宋体。正文、按钮、输入、工具卡、时间戳一律 Geist / 系统无衬线。
- **发丝线 + 一层玻璃**：层次靠 `1px` 半透明边框和表面明度差；只有顶栏、底部导航、抽屉、Toast、悬浮按钮用玻璃（半透明 + `backdrop-filter`）。聊天气泡、卡片不用玻璃。
- **18px 点阵**：仅用于发现页 hero、空状态、年龄门背景。它 是环境纹理，不铺在正文、表单和聊天列表上。
- **夜间密度**：正文 14–15px，元信息 10–11px，聊天气泡 14.5px。比桌面工作区松，但比消费端海报克制。
- **留白是情绪**：聊天页允许大面积空白；不要在空白处塞推荐、广告、运营位。

情绪目标：深夜、纸本、安静、有一点危险感，但不廉价。不做彩虹渐变、不做大面积霓虹、不做玻璃叠玻璃、不做慢动效。

## Colors

两套主题共用语义令牌；暗色是默认，亮色在 `html[data-theme="light"]` 覆盖同名变量。

**暗色 Night Craft**

| 令牌 | 值 | 用途 |
| --- | --- | --- |
| `--bg` | `#101114` | 页面底色 |
| `--bg-deep` | `#0b0c0e` | 聊天 / 沉浸页更深一档 |
| `--fg` | `#f3f0e8` | 米白正文 |
| `--surface` | `#1b1b1d` | 卡片、气泡、输入区、底部导航 |
| `--raised` | `#222224` | 抽屉、浮层、预览 |
| `--sunken` | `#171719` | 输入框、图片占位、下沉块 |
| `--hover` | `#2a2a2c` | 悬停 / 按压底 |
| `--muted` | `#9f988b` | 次要文字 |
| `--subtle` | `#746f66` | 更弱的提示、时间戳 |
| `--accent` | `#e8a532` | 唯一强调色 |
| `--accent-hover` | `#f2b64b` | 主操作悬停 |
| `--on-accent` | `#17110a` | 琥珀上的深墨字 |
| `--danger` | `#e46c5b` | 错误、删除、停止 |
| `--danger-fill` | `#c14b3d` | 危险实心按钮 |
| `--border` | `rgb(243 240 232 / .15)` | 全部发丝线 |
| `--border-strong` | `rgb(243 240 232 / .24)` | 玻璃描边、头像描边 |
| `--selection` | `rgb(232 165 50 / .28)` | 文本选中 |
| `--dot` | `rgb(232 165 50 / .13)` | 18px 点阵 |
| `--glass` | `rgb(16 17 20 / .66)` | 玻璃底 |
| `--glass-filter` | `blur(22px) saturate(132%)` | 顶栏 / 底栏 / 抽屉 |

**亮色 Japanese Minimal**

| 令牌 | 值 |
| --- | --- |
| `--bg` | `#f7f1e8` |
| `--bg-deep` | `#f2e8da` |
| `--fg` | `#302821` |
| `--surface` | `#fffdf8` |
| `--raised` | `#faf5ed` |
| `--sunken` | `#f2e8da` |
| `--hover` | `#f2e8da` |
| `--muted` | `#75665a` |
| `--subtle` | `#99887a` |
| `--accent` | `#b34631` |
| `--accent-hover` | `#9c3a28` |
| `--on-accent` | `#fffaf2` |
| `--danger` | `#b94a43` |
| `--border` | `rgb(48 40 33 / .17)` |
| `--dot` | `rgb(48 40 33 / .10)` |

颜色纪律：

- 每个模式只有一个强调色相。成功不另造绿色，用 `--accent` 或正文色；警告用 `--danger` 的弱化版。
- 强调色出现位置：主按钮、在线点、选中筛选、当前导航、亲密度条、播放按钮、工具卡运行态、图片配文的高亮。
- **人设封面是唯一允许出现多色的区域**：每个角色有 `palette: [深色, 暖色]`，用于渐变 + 线稿。它属于内容，不属于 UI。
- 用户气泡使用强调色 13% 混入表面色，不是实心琥珀；避免大面积高亮。
- 不做暗色 `filter: brightness()` 就地提亮；用 `--accent-hover`。

```yaml
colors:
  background: "#101114"
  background-deep: "#0b0c0e"
  foreground: "#f3f0e8"
  surface: "#1b1b1d"
  surface-raised: "#222224"
  surface-sunken: "#171719"
  surface-hover: "#2a2a2c"
  primary: "#e8a532"
  on-primary: "#17110a"
  primary-hover: "#f2b64b"
  muted: "#9f988b"
  subtle: "#746f66"
  border: "rgb(243 240 232 / .15)"
  border-strong: "rgb(243 240 232 / .24)"
  danger: "#e46c5b"
  danger-fill: "#c14b3d"
  selection: "rgb(232 165 50 / .28)"
  dot: "rgb(232 165 50 / .13)"
  glass: "rgb(16 17 20 / .66)"
```

**阴影与微光**只有四档：

```css
--shadow:        inset 1px 1px 0 rgb(243 240 232 / .18), 0 18px 48px rgb(16 17 20 / .24);
--shadow-strong: 0 24px 68px rgb(16 17 20 / .44);
--glow:          0 0 14px rgb(232 165 50 / .18);
--shadow-inset:  inset 0 0 0 1px var(--accent);
```

普通卡片无阴影；只有抽屉、悬浮「回到最新」、主按钮、Toast 和输入区获得阴影 / 微光。

## Typography

- **Display（36–54px，衬线）**：发现页主标题「今晚，想和谁说话？」。手机用 `clamp(36px, 10vw, 54px)`，行高 1.04，字距 `-1.6px`。中文大标题必须负字距。
- **Headline（27–44px，衬线）**：页面标题「消息 / 我的 / 今晚精选」。移动端 27–34px。
- **Title（18–22px，衬线）**：人设卡名、聊天头部名、抽屉区标题。人设卡名 19px。
- **Body（14–16px，无衬线）**：聊天气泡 14.5px / 1.62；抽屉正文 13px / 1.85；正文列表 12px。
- **Label（9–11px，无衬线）**：时间戳、在线状态、工具卡、徽标、底部导航、eyebrow。
- **Eyebrow（10px / 800 / 字距 1.4px / 大写 / 强调色）**：区块上方的大写小标，如 `AFTER HOURS`、`TONIGHT'S PICK`、`A PRIVATE LINE`。

字族：

```css
--font-display: Georgia, "Songti SC", "Noto Serif SC", "Times New Roman", serif;
--font-ui: "Geist Variable", -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
```

衬线只使用 700；正文只使用 400/500/600。不引入 300 或 800 的正文。

```yaml
typography:
  display:
    fontFamily: Georgia, "Songti SC", "Noto Serif SC", serif
    fontSize: clamp(36px, 10vw, 54px)
    fontWeight: 700
    lineHeight: 1.04
    letterSpacing: -1.6px
  page-title:
    fontSize: clamp(34px, 9vw, 44px)
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: -1.2px
  section-title:
    fontSize: 27px
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: -0.8px
  persona-name:
    fontSize: 19px
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: -0.4px
  chat-body:
    fontFamily: "Geist Variable", "PingFang SC", sans-serif
    fontSize: 14.5px
    fontWeight: 400
    lineHeight: 1.62
  body:
    fontSize: 13px
    lineHeight: 1.85
  meta:
    fontSize: 10.5px
    lineHeight: 1.5
  label:
    fontSize: 10px
    fontWeight: 800
    letterSpacing: 1.4px
    textTransform: uppercase
```

## Layout

### 手机外壳

- 基准视口 **390 × 844**（iPhone 14 / 15），兼容 320–430。
- 页面 `min-height: 100dvh`，不锁 `100vh`；输入框聚焦时浏览器可以压缩可视区。
- 页面左右留白 `--page-x: 20px`（桌面 46px）。
- 底部导航 `60px + safe-bottom`；`position: fixed`，宽 `min(100%, 720px)`，居中。
- 顶栏 58px；吸顶时背景 92% 页面色 + 18px blur，底部发丝线。
- 聊天页是独立 `100dvh` 三段的 flex：头部 58px / 消息区 `flex:1 min-height:0 overflow-y:auto` / 输入区自适应。
- 所有固定底部的元素（导航、输入区、Toast）必须加 `env(safe-area-inset-bottom)`。
- 触控目标 ≥ 44px（主要按钮 46px，图标按钮 38px 外套 44px 点击区，底部导航整格可点）。

### 发现页

1. 品牌顶栏：左 `plot.18` 字标，右「13 位今晚在线」+ 登录 / 头像。
2. Hero：点阵 + 琥珀光晕，eyebrow → 大标题 → 副标题 → 搜索框 → 成年提示。
3. 筛选横滑：34px 药丸，选中为强调色 10% 底 + 48% 描边 + 强调色字。
4. 今晚精选：横向 snap，卡片 78vw / 最大 310px，4:5。
5. 所有人：两列网格（≥560px 三列，≥900px 四列），卡片 3:4。
6. 页脚：品牌 + 成年人提示。

### 聊天页

- 头部：返回 38×38、头像 36、名字 16 衬线、状态 9.5（在线点 + 关系阶段 + 第几天）、更多。
- 消息区：最大宽 680，左右 14px；日期分组；她左、他右。
- 气泡：最大 82%，圆角 17px，靠说话者一侧下角 5px；她的是表面色 + 发丝线，他的是强调色 13% + 强调色 24% 描边。
- 工具卡：23px 高药丸，只在运行态出现（强调色 + 脉冲点），完成后消失；失败由角色文本说明。
- 图片：宽 `min(72vw, 310px)`、最大高 410px、圆角 16px；配文叠在底部渐变上。
- 语音：30px 圆形播放键 + 20 根波形 + 秒数；播放进度用强调色亮度表示。
- 输入区：24px 圆角外壳，左右相机 38 + 文本 + 发送 38（有内容时琥珀）。发送中变成 danger 方形停止键。
- 空对话：`A PRIVATE LINE` + 一句说明 + 四个开场建议。
- 滚动时「回到最新」悬浮在输入区上方 96px。

### 抽屉（Sheet）

- 移动端从底部升起，92dvh，顶部 24px 圆角，拖拽条 38×4。
- 桌面端居中，最大 720px，86vh，全圆角。
- 抽屉头固定（标题 + 关闭），正文独立滚动。
- 人设详情：全宽 hero 230–330px → 事实行 → 标签 → 关于她 → 说话方式 → 你们之间 → 开场建议 → 主 CTA。
- 弹层里不再叠玻璃卡片；用发丝线分区。

```yaml
spacing:
  unit: 2px
  xxs: 4px
  xs: 6px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 22px
  xxl: 30px
  section: 44px
  page-gutter-mobile: 20px
  page-gutter-desktop: 46px
  header-height: 58px
  chat-header-height: 58px
  bottom-nav-height: 60px
  control-height: 46px
  icon-button: 38px
  composer-radius: 24px
  sheet-radius: 24px
```

## Elevation & Depth

深度只表达「谁浮在上面」：

1. **普通层**：页面、卡片、气泡、输入区 → 1px 发丝线，无阴影。
2. **吸顶层**：顶栏、聊天头、底部导航 → 92% 页面色 + blur + 底部/顶部发丝线。
3. **浮层**：抽屉、Toast、回到最新、图片灯箱 → `--raised` / `--glass` + `--shadow-strong`。
4. **强调层**：主按钮、在线点、运行中的工具卡 → `--glow`。

不要给聊天气泡加阴影；不要在玻璃上叠玻璃；不要手写 `z-index` 堆叠，按 12（聊天头）/ 20（发现顶栏）/ 40（底部导航）/ 60（抽屉）/ 90（Toast）/ 100（灯箱）/ 200（年龄门）。

过渡：`--motion: .18s cubic-bezier(.2,.7,.2,1)`。只动 `border-color / color / background / box-shadow / transform / opacity`。按下统一 `scale(.98)`。尊重 `prefers-reduced-motion`。

## Shapes

- 控件：4–6px（输入框、按钮内层、图标按钮）。
- 卡片：18px（人设卡、聊天图片、抽屉内分组）。
- 大块：24px（抽屉、输入外壳、主按钮全圆）。
- 全圆：主按钮、筛选药丸、标签、在线点、发送键、语音播放键、底部导航无。
- 气泡：17px，说话者一侧下角 5px。
- 头像：50%。
- 人设卡：18px；精选卡：18px；后台卡片：12px。

```yaml
rounded:
  xs: 2px
  sm: 4px
  md: 6px
  lg: 8px
  xl: 12px
  2xl: 18px
  3xl: 24px
  bubble: 17px
  bubble-tail: 5px
  full: 999px
```

## Components

### Buttons

- **主按钮**：琥珀底 + 深墨字，46px 高，全圆，14px/600；一屏最多一个。
- **Soft**：表面底 + 发丝线 + 14px 字；悬停只改边框和文字为强调色。
- **图标按钮**：38×38，4px 圆角，默认 muted，悬停 / 激活是 hover 底 + 强调色。
- **危险**：danger-fill 底 + 米白字；只用于删除 / 不可逆。
- **文字链接**：11–12px，muted；悬停变正文色。
- 焦点：全局 `outline: 2px solid var(--accent); outline-offset: 3px`，组件里不重写。

### Persona Card

- 3:4，人设封面是「双色渐变 + 线稿 + 首字」的生成式美术；若后台上传真实图片，遵循同一裁切。
- 底部渐变从 38% 开始加深，保证名字可读。
- 左上在线点，右上年龄胶囊（22px 高、玻璃底）。
- 名字衬线 19px，职业 10px 半透明白，标签最多两个（22px 玻璃药丸）。
- 按压 `scale(.985)`；桌面悬停 `translateY(-2px)` + 封面 `scale(1.025)` + 强调色边框。

### Featured Card

- 4:5，宽 78vw / 最大 310px，横向 snap。
- 内容在底部：eyebrow、27px 衬线名、11.5px 副标题、CTA「认识她 →」。
- 与普通卡共用封面组件，但文字更大、更海报化。

### Persona Detail Sheet

- 全宽 hero + 底部渐变；eyebrow `MEET {NAME}`、34–42px 衬线名 + 年龄、tagline。
- 事实行：城市、职业、语言，11px muted。
- 标签行：所有 tag。
- 分区标题 18px 衬线；正文 13px / 1.85。
- 关系条：认识天数 + 阶段 + 3px 亲密度条。
- 开场建议：34px 药丸，最多四个。
- CTA 固定在内容流末尾，46px 全宽。

### Chat Bubbles & Tool Chips

- 她：左对齐，头像 30px（只在连续 assistant 的第一条显示），表面色气泡。
- 你：右对齐，无头像，强调色 13% 气泡。
- 工具卡只在工具运行中出现（强调色 + 脉冲点），完成后消失；失败由角色用文字说明，不把技术红框展示给用户。工具卡不是按钮，不能点。
- 图片消息与气泡同列；配文叠在图片底部；点击进入全屏灯箱。
- 语音消息是 250px 以内的横向面板；播放键 30px 琥珀圆。
- 失败回复下方出现 danger 文案 + 「再试一次」下划线按钮。
- 流式文本末尾有 5px 琥珀光标闪烁；无正文时显示三点输入气泡。

### Composer

- 外层是 `--surface` 88% + 发丝线 + 24px 圆角 + `--shadow`；聚焦时边框 36% 强调色 + `--glow`。
- 相机按钮 38×38，文本域 16px（防 iOS 聚焦缩放），最大高 116px，自动长高。
- 发送键 38×38；无内容时透明 + subtle，有内容时琥珀 + 深墨 + 微光；生成中换成 danger 停止。
- 图片预览 56×56、8px 圆角、右上 18px 移除按钮；上传中显示 10px 强调色提示。
- 输入区下方一行 9px 免责声明，不能省略。

### Age Gate

- 全屏，点阵 + 顶部径向光晕；面板 440px，玻璃面，30px 内边距。
- eyebrow `BEFORE WE BEGIN`；34–42px 衬线标题「今夜之前，先确认一件事。」。
- 两段正文：一段说明虚构成年人；一段说明 18+ 与可随时退出。
- 主按钮 46px 全宽；下方「我还没准备好」10px subtle 链接。
- 没有关闭按钮；必须明确确认才能进入。

### Bottom Nav

- 60px + safe-bottom；玻璃面 + 顶部发丝线；三项等分。
- 图标 21px + 9px 文字；激活为强调色，图标有 6px 柔光。
- 聊天页不显示底部导航（全屏对话）。

### Admin Console

- 不复用手机聊天的松密度：顶栏 56px、标签栏 34px、表格行 44px、后台卡片 12px 圆角。
- 桌面 270px 人设列表 + 自适应编辑器；移动端单列。
- 表单标签 11px muted；输入 48px / 16px；复选框卡 17px。
- 工具 / Skills 用两列复选框卡（≥640px），每张卡包含名字、描述、可用状态。
- 保存按钮 sticky 在底部；危险操作是图标按钮 + 二次确认。
- 后台也使用同一套颜色令牌，不另建主题。

## Mobile Interaction

- **键盘**：`interactive-widget=resizes-content` + `100dvh`；输入框聚焦后 240ms 把光标滚入可视区。文本域 16px 防止 iOS 自动放大。
- **滚动**：聊天消息区独立滚动，`overscroll-behavior: contain`，不让页面跟着弹。自动滚到底，仅在用户已经接近底部时；用户上滑后显示「回到最新」。
- **图片**：相册 / 相机由系统选择器决定，不强制 `capture`。发送前在浏览器压到最长边 1600 / JPEG 0.86。
- **长按 / 右键**：不做隐藏菜单；所有操作显式可见（更多、删除、重试）。
- **加载**：人设列表用骨架卡；聊天首屏用 `CONNECTING` 文案；上传用输入区提示，不用全屏遮罩。
- **失败**：错误只出现在出错的消息下方；重试是显式按钮；网络断开不弹系统 alert。
- **触觉**：可选 `navigator.vibrate(8)`，只在发送 / 收到图片时；不支持就静默跳过。
- **PWA**：`manifest.webmanifest` + `theme-color` + apple-touch-icon；standalone 时保持安全区。

## Accessibility

- 正文与背景对比度 ≥ 4.5:1；muted 只用于非关键信息；subtle 不用于可读正文。
- 所有图标按钮有 `aria-label`；图片有 `alt`；抽屉有 `role="dialog" aria-modal`；Toast 用 `aria-live="polite"`。
- 焦点环可见且不被 `overflow` 裁掉；抽屉打开时锁定背景滚动，Esc / 点遮罩关闭。
- 不依赖 hover 才能完成操作；触控目标 ≥ 44px。
- 支持 `prefers-reduced-motion`；动效不超过 240ms。
- 颜色不是唯一信息：在线点旁有文字状态；工具卡有文字标题；失败有文案。

## Do's and Don'ts

- **Do** 只用 `tokens.css` 的语义令牌；组件里不出现 `#E8A532` 字面值。
- **Do** 衬线只做标题、人设名、品牌；正文、按钮、输入、工具卡一律无衬线。
- **Do** 用 `gap` 排版，不用 `space-x-*`；方形元素用 `size-*` 思路；溢出用 `truncate`。
- **Do** 用 1px 发丝线建立层次；普通气泡 / 卡片不加阴影。
- **Do** 把聊天页做成三段 flex，消息区 `min-height: 0`，输入区不遮消息。
- **Do** 给所有底部固定元素加 safe-area；给所有输入 16px 字号。
- **Don't** 新增第二个品牌色相；不要给人设卡分配 UI 色相，颜色只来自封面。
- **Don't** 在聊天里塞营销位、推荐卡、广告、任务系统。
- **Don't** 给普通卡片铺玻璃或发光；玻璃只给顶栏 / 底栏 / 抽屉 / Toast / 悬浮按钮。
- **Don't** 用 hover-only 的交互；手机没有 hover。
- **Don't** 在浮层上手动写 `z-index` 叠罗汉；按上面的层级表。
- **Don't** 把系统提示词、工具清单、Skills 正文展示给用户；这些是后台配置。
- **Don't** 用「AI 助手」口吻写文案；界面文案是深夜的、克制的、具体的，不喊口号。
