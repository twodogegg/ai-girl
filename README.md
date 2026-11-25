# PLOT18 · AI 选女友聊天

一个手机优先的 AI 陪伴聊天站：浏览人设 → 进入一段只属于你和她的对话 → 聊天、发照片、收到她的自拍与语音。  
每个角色都有独立的人设提示词、工具白名单与 Skills；**用户看不到、也不能自选 Skill**，全部由主理人在后台配置。

> 所有角色均为 18 岁以上的虚构成年人。产品仅面向 18 岁以上用户，首次进入需要成年确认。

---

## 现在能做什么

- **发现 / 选择**：13 个人设，暖黑 + 琥珀的 Night Craft 视觉；支持标签筛选、搜索、精选横滑、详情抽屉。
- **聊天**：NDJSON 流式回复、输入中状态、停止、失败重试、历史消息、关系阶段与亲密度。
- **发照片**：相册 / 相机选图 → 浏览器压缩 → 私有上传 → 视觉模型读图；她能看到并回应照片。
- **她发照片 / 语音**：服务端工具 `send_photo` / `send_voice`，生成后作为图片 / 语音气泡落进对话。
- **长期记忆**：`remember` / `recall` 工具 + 每轮注入重要记忆；「她记得的事」里可以逐条查看、删除。
- **关系状态**：`update_relationship` 工具更新 mood / affinity / stage，聊天头部与详情页实时显示。
- **后台配置**：`/admin` 编辑每个人设的提示词、工具、Skills、开场白、头像配色、温度、上下架。
- **Skills 渐进加载**：模型上下文里只有 Skill 简介，需要时调用 `activate_skill` 取正文；用户端没有任何 Skill 入口。
- **演示模式**：没有配置文本模型时自动启用本地演示引擎，仍会真实调用记忆 / 关系 / 自拍工具，方便先验收 UI。
- **手机细节**：`100dvh`、安全区、44px 触控、16px 输入框防 iOS 缩放、底部导航、底部抽屉、深浅两套主题、可添加到主屏的 manifest。

---

## 快速开始

要求：Node 20+、Python 3.12+、[uv](https://docs.astral.sh/uv/)。

```bash
cp .env.example .env.local      # 填 LLM_API_KEY；不填就是演示模式
npm --prefix frontend install
uv sync --project backend

bash scripts/dev.sh             # API :5190 + Web :5191
```

打开 <http://127.0.0.1:5191>；终端同时会打印局域网地址，手机连同一个 Wi-Fi 也能直接打开。生产构建：

```bash
npm --prefix frontend run build
uv run --project backend python -m app   # 后端会直接托管 frontend/dist
```

> 端口 5190 / 5191 是占用检查后选的；后端可用 `PORT` 环境变量改，前端改 `frontend/vite.config.ts`，Vite 代理会自动跟随 `PORT`。
>
> `npm run dev` 默认监听 `0.0.0.0`，同一 Wi-Fi 可直接访问；只想本机访问用 `HOST=127.0.0.1 npm run dev`。

### 局域网访问（手机 / 同 Wi-Fi 设备）

开发模式默认就是局域网可访问（热更新照样生效）：

```bash
npm run dev
```

终端会打印本机局域网地址，例如 `http://192.168.1.23:5191`，在手机上直接打开即可。Vite 负责页面与 `/api` 代理，Cookie 同源，`PUBLIC_ORIGIN` 保持为空。

生产模式（后端托管 `frontend/dist`，只有一个端口）：

```bash
npm run build
npm run start:lan      # 等价于 HOST=0.0.0.0 uv run --project backend python -m app
# 打开 http://<本机局域网 IP>:5190
```

也可以把 `HOST=0.0.0.0` 写进 `.env.local`，之后 `npm run dev:api` / `python -m app` 都会监听所有网卡。查看本机 IP：

```bash
ipconfig getifaddr en0        # Wi-Fi；有线网卡通常是 en1
```

注意事项：

- 手机和电脑要在同一网段；路由器开了「访客网络 / AP 隔离」会阻断互访。
- 首次监听 `0.0.0.0` 时 macOS 可能弹防火墙提示，需要允许 `node` / `python` 接受传入连接。
- 局域网是明文 HTTP，只适合可信网络。给别人用之前，务必在 `.env.local` 改掉 `ADMIN_PASSWORD` / `DEMO_PASSWORD`，或设 `DEMO_USER_ENABLED=false`；不需要局域网时用 `HOST=127.0.0.1 npm run dev`。
- 用 `xxx.local` 这类 mDNS 主机名访问时，`npm run dev` 已自动放行 `.local`；其他域名用 `VITE_ALLOWED_HOSTS=a.example.com,b.example.com` 追加。
- 相册选图在 HTTP 下可用；以后若加实时摄像头 / 麦克风采集，浏览器要求 HTTPS（`localhost` 除外），到时要配反向代理或自签证书，并把 `COOKIE_SECURE` 设为 `true`。

### 默认账号

| 账号 | 密码 | 用途 |
| --- | --- | --- |
| `admin` | `change-me-now` | 主理人后台 `/admin` |
| `demo` | `demo1234` | 普通体验账号 |
| 访客 | 一键进入 | 无需密码的临时账号 |

上线前务必在 `.env.local` 改掉 `ADMIN_PASSWORD` / `DEMO_PASSWORD`，或设置 `DEMO_USER_ENABLED=false`。

---

## 配置

所有配置都在 `.env.local`（或环境变量）：

| 变量 | 说明 |
| --- | --- |
| `HOST` / `PORT` | 后端监听地址与端口。默认 `127.0.0.1:5190`；局域网 / 手机访问设为 `0.0.0.0` |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | 任意 OpenAI Chat Completions 兼容网关。默认模型 ID 是 `claude-sonnet-5-5`，可换成网关实际模型名 |
| `LLM_VISION` | 模型是否支持图片输入；为 `false` 时用户照片只作为文字提示 |
| `IMAGE_BASE_URL` / `IMAGE_API_KEY` / `IMAGE_MODEL` / `IMAGE_SIZE` | 自拍生成。OpenAI `/v1/images/generations` 兼容接口；未配置时 `send_photo` 返回不可用 |
| `TTS_BASE_URL` / `TTS_API_KEY` / `TTS_MODEL` / `TTS_VOICE` | 语音生成。OpenAI `/v1/audio/speech` 兼容接口 |
| `DATABASE_PATH` / `DATA_DIR` | SQLite 与上传文件位置，默认 `data/` |
| `ADMIN_*` / `DEMO_*` | 首次启动自动创建的后台 / 演示账号 |
| `COOKIE_SECURE` | HTTPS 部署时设为 `true` |
| `PUBLIC_ORIGIN` | 只有前后端跨域直连才需要；同源部署留空 |
| `MAX_UPLOAD_MB` / `MAX_CONTEXT_MESSAGES` / `MAX_TOOL_ROUNDS` / `RATE_LIMIT_PER_MINUTE` | 上传、上下文、工具轮数、限流上限 |

没有 `LLM_API_KEY` 时会进入**本地演示模式**：不调用外部模型，但记忆、关系、自拍（若配置了图床）等工具仍按真实路径执行。聊天页顶部会明确标注「演示模式」。

---

## 后台：每个人设独立的 Agent 配置

访问 `/admin`，用管理员账号登录。

- **人设**：`id`、中英文名、年龄（强制 18+）、城市、职业、一句话介绍、小传、性格、说话方式、关系动态、补充设定、完整提示词覆盖。
- **开场**：第一句话、四个开场建议、封面色 A/B、时区、排序、上架开关。
- **工具**：勾选后才挂到该人设的模型上。用户端不出现工具列表，也没有审批。
- **Skills**：勾选后该人设可用；模型只看到简介，需要时自己 `activate_skill`。`always-on` 的 Skill 正文会直接注入。
- **Skills 库**：单独编辑名称、简介、分类、正文（Markdown）、是否 always-on。
- **概览 / 用户**：对话量、消息量、记忆量、最近对话、用户停用。

新增一个工具 / Skill 的扩展方式见 [docs/chat-system.md](docs/chat-system.md)。

---

## 架构

```
frontend/  React 19 + Vite + TypeScript（无 UI 框架，纯语义 CSS）
  ├─ /                    发现：人设卡片 / 精选 / 筛选
  ├─ /chats               消息列表
  ├─ /chat/:personaId     聊天：NDJSON 流、工具卡、图片、语音
  ├─ /me                  我的：主题、成年状态、退出
  ├─ /admin               人设 / Skills / 用户后台
  └─ api/                 统一 fetch 与流式解析

backend/   FastAPI + SQLite + OpenAI 兼容模型
  ├─ routers/             auth / personas / chat / files / admin
  ├─ services/
  │   ├─ agent.py         系统提示 → 流式模型 → 工具循环 → 落库
  │   ├─ tools.py         记忆 / 关系 / 自拍 / 语音 / 时间
  │   ├─ personas.py      人设卡、Skills 装配、系统提示
  │   ├─ conversations.py 会话与消息
  │   ├─ memory.py        长期记忆
  │   ├─ media.py         图片重编码、私有文件
  │   └─ studio.py        生图 / TTS
  └─ seed.py              13 个人设与 7 个官方 Skills
```

更完整的聊天链路、协议、数据模型和安全边界见：

- [design.md](design.md) · 视觉与手机端设计系统
- [docs/chat-system.md](docs/chat-system.md) · 聊天系统设计（从 darl-tv 移植/改造的说明）

---

## 测试

```bash
uv run --project backend pytest backend/tests
uv run --project backend ruff check backend
npm --prefix frontend run build
```

联调完整工具链（不需要真实模型 / 图床）：

```bash
# 终端 1：假 OpenAI 服务（文本 / 生图 / 语音）
uv run --project backend python scripts/mock-openai.py

# 终端 2：让 API 指向假服务
LLM_BASE_URL=http://127.0.0.1:5196/v1 LLM_API_KEY=mock LLM_MODEL=mock \
IMAGE_BASE_URL=http://127.0.0.1:5196/v1 IMAGE_API_KEY=mock \
TTS_BASE_URL=http://127.0.0.1:5196/v1 TTS_API_KEY=mock \
uv run --project backend python -m app
```

然后聊天里说「给我看看你」会走 `send_photo`，说「给我发条语音」会走 `send_voice`，发一张图会走视觉输入。

---

## 内容与安全

- 首次进入强制 18+ 确认；后台保存人设时也会校验年龄 ≥ 18。
- 所有角色设定为虚构成年人，系统提示要求模型不跳出人设、不冒充真人、不涉及未成年人 / 真实人物 / 非自愿内容。
- 用户照片仅自己与当前对话可见；上传时去 EXIF、重新编码为 JPEG，文件读取校验归属。
- 人设提示词、工具白名单、Skills 正文只存在于后台接口，公开接口不返回。
- 聊天接口有每用户每分钟限流，同一人设同时只允许一轮生成。
- 这是产品原型，不是心理 / 医疗 / 危机干预服务。上线前请按目标市场补齐内容审核、付费订阅、退款与数据合规流程。

---

## 已知边界 / 下一步

- 上下文目前是「最近 48 条 + 重要记忆」，还没有滚动摘要；长对话后续可加摘要任务。
- 未接支付 / 订阅 / 积分；人设里已保留 `sort`、`published` 等运营字段。
- 未做推送、多端同步撤销、举报后台和内容审核队列。
- 单机 SQLite + 内存限流 / 运行互斥；多实例部署时需要换 MySQL/Postgres、Redis 限流与共享运行锁。
- 人设封面目前是「渐变 + 线稿 + 首字」的生成式美术，后台可继续接真实图片上传与审核。
