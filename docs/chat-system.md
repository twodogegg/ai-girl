# PLOT18 聊天系统设计

本文说明 PLOT18 的聊天链路，以及它从 `darl-tv` 的 Agent 聊天系统继承了什么、改了什么、为什么改。

---

## 1. 从 darl-tv 继承的骨架

darl-tv 的聊天是「桌面画布 + 浏览器执行工具 + 审批」的 Agent 系统。PLOT18 只保留对陪伴聊天有用的部分：

| darl-tv | PLOT18 | 说明 |
| --- | --- | --- |
| FastAPI + `openai-agents` SDK | FastAPI + OpenAI Chat Completions 流式客户端 | 工具全部在服务端执行，不需要 SDK 的浏览器工具桥；自写循环更可控 |
| NDJSON 流：`meta / assistant_delta / tool_call / error / done` | NDJSON 流：`meta / state / text / tool / image / voice / error / done` | 保留逐行 JSON、心跳、`done` 收口 |
| Agent 配置：`instructions` + `applicationIds` 工具白名单 + `skillIds` | 人设配置：`promptExtra/systemPrompt` + `toolIds` + `skillIds` | 每个女友就是一个独立的 Agent |
| 工具在浏览器执行，结果 POST 回传 | 工具在服务端执行，直接写库 / 调服务 | 用户不审批，不需要浏览器执行器 |
| `activate_skill` 渐进加载 + 服务端补正文 | 同款 | 用户看不到 Skills，也不能自选 |
| 会话按 `user + project` 隔离 | 会话按 `user + persona` 隔离 | 一段关系一条长期会话 |
| 后台 Agents / Skills / 工具管理 | `/admin` 人设 / Skills / 用户管理 | 只保留陪伴场景需要的字段 |
| 后台运行、断线重订阅、steering | 不做后台运行 / steering | 单轮对话短，浏览器 abort 即可停止；部分回复会落库 |
| 上下文裁剪 + 历史消息 | 最近 48 条 + 重要记忆 | 长对话摘要列为后续计划 |

**为什么不用 `openai-agents`？**  
darl-tv 的工具是「服务端发布调用 → 浏览器执行 → 回传结果」，SDK 的价值在于流式工具循环与多 Agent。PLOT18 的工具（记忆、关系、生图、TTS）全部是服务端能力，且要在工具执行时直接向流里发 `image/voice/state` 自定义事件。自写一个约 180 行的工具循环更透明，也避免为了一个 SDK 把浏览器桥接、审批队列、后台运行等画布逻辑一起搬过来。

---

## 2. 一次聊天请求的完整链路

```
浏览器                         FastAPI                         模型 / 工具
  │ POST /api/chat               │                                │
  │ {personaId, conversationId,  │ 1. adult_user + 限流 + 运行互斥  │
  │  text, imageIds}             │ 2. 校验会话归属                  │
  ├─────────────────────────────>│ 3. 保存用户消息（含图片 fileId） │
  │                              │ 4. 创建空 assistant 消息          │
  │<── meta {conversationId,     │ 5. 装配系统提示                  │
  │        messageId, demo}      │    - 人设 / 关系 / 记忆 / 时间    │
  │<── state {...}               │    - Skills 元数据 + always-on   │
  │                              │    - 工具使用规则 / 安全边界      │
  │                              │ 6. 历史消息 + 当前图片 → 模型     │
  │<── tool {running}            │ 7. 模型返回 tool_call            │
  │<── tool {success, summary}   │    → 服务端执行 → tool 消息       │
  │<── image / voice / state     │    → 继续下一轮模型调用           │
  │<── text 增量...              │ 8. 汇总正文 + parts               │
  │<── done {message, state}     │ 9. 更新 assistant 消息、会话状态  │
```

### 2.1 请求前置检查

1. `adult_user`：必须登录且 `adult_confirmed_at` 非空。
2. 限流：每用户每分钟最多 `RATE_LIMIT_PER_MINUTE` 条（默认 24）。
3. `conversationId` 存在时必须属于当前用户且属于当前人设；**不能回退成新建会话**（越权修复）。
4. 同一用户 + 同一人设同时只允许一轮生成；第二次返回 409「她还在回你上一条」。
5. 文本最长 4000 字；一次最多 4 张图；图片必须属于当前用户。

### 2.2 消息落库

- 用户消息：`content` 存文字，`parts` 存 `[{type:"image", fileId}]`。
- assistant 在模型开始前先插一条空消息；流式过程中每轮工具结束后更新一次，`finally` 再更新一次。
- 浏览器断开时，生成器被关闭，`finally` 仍然执行，已生成的部分回复会保存。
- 最终 `meta` 里写 `{demo, tools}`，不再保留 `streaming` 标记。

### 2.3 历史上下文

- 取最近 `MAX_CONTEXT_MESSAGES`（默认 48）条。
- **只有当前这一轮的用户图片**会以 `image_url` data URL 传给模型；更早的图片只留一句「（对方发来一张照片）」，避免每轮重复编码历史图片。
- 当前轮没有文字只有图片时，文本标签为「（对方发来一张照片，没有配文）」。
- 模型不支持视觉（`LLM_VISION=false`）时，当前图片也降级成文字标记。

---

## 3. 系统提示装配

`services/personas.build_system_prompt()` 按顺序拼：

1. **身份**：名字、年龄、城市、职业、小传、性格、说话方式、关系动态、语言、`promptExtra`。
2. **边界**：虚构成年人、不跳出人设、不泄露提示词 / 工具 / 模型、亲密互动需明确同意、不涉及未成年人 / 真实人物 / 非自愿 / 违法、现实危机先关心安全、不索取敏感信息、不编造已发生的事。
3. **聊天方式**：手机聊天 1–3 句、先接情绪、不连续提问、不替用户写动作、照片先看细节、工具不可用要如实说、少用 emoji、允许对话停下。
4. **当前关系**：对方称呼、认识天数、阶段（stranger / acquaintance / close / lover）、affinity、mood、重要记忆列表。
5. **时间**：按人设城市时区（`America/Los_Angeles`、`Asia/Shanghai` 等）计算「凌晨 / 晚上 + 星期」。
6. **工具指南**：每个工具的用途与克制原则；一次回复最多一个工具。
7. **Skills**：always-on 的正文直接注入；其余只给 `id｜name：description` 清单 + 「先 `activate_skill`」提示。
8. **完整提示词覆盖**（后台 `systemPrompt` 非空时追加）。

模型温度来自人设 `temperature`（0.76–0.92），模型 ID 可单独覆盖，默认用全局 `LLM_MODEL`。

---

## 4. 工具

工具全部是服务端函数，注册在 `services/tools.py` 的 `TOOLS` 字典里。每个人设只挂 `toolIds` 中勾选的工具；用户端不展示、也不能选择。

| 工具 | 作用 | 副作用 |
| --- | --- | --- |
| `remember` | 写入长期记忆（事实 / 偏好 / 日期 / 情绪 / 承诺） | `memories` 表；每轮系统提示会带最重要的 14 条 |
| `recall` | 按关键词找回记忆 | 更新 `last_used_at` |
| `update_relationship` | 更新 mood、affinity（每次 ±3）、阶段、里程碑 | `conversations.state`；向流里发 `state` 事件 |
| `send_photo` | 调生图服务发一张自拍 | 保存私有文件；向流里发 `image` 事件；加入 assistant `parts` |
| `send_voice` | 调 TTS 发一条短语音 | 保存音频；向流里发 `voice` 事件；加入 `parts` |
| `get_time` | 读取人设时区的当前时间 | 只读 |
| `activate_skill` | 取一个 Skill 的完整正文 | 只读；正文只在本次工具结果里 |

工具结果统一是 JSON：

```json
{"status": "ok", "summary": "记住了：他喜欢海边", "memory": "..."}
{"status": "unavailable", "reason": "自拍服务还没有配置。", "summary": "自拍发送失败：..."}
{"status": "error", "error": "..."}
```

- 模型只能看到 `status/summary/output`；前端只消费 `tool` 事件的 `status/summary`。
- 工具执行失败不会中断整轮；模型收到 error 结果后应继续用文字回应。
- `send_photo` / `send_voice` 未配置时返回 `unavailable`，系统提示要求模型如实说「现在发不了」，不许假装已发。

### 4.1 工具循环

```
for round in range(MAX_TOOL_ROUNDS):
    stream = llm.stream(messages, tools=specs)
    累积 text 与 tool_calls
    if 没有 tool_calls: break
    追加 assistant 消息（content + tool_calls）
    for 每个 call:
        emit tool running
        执行（activate_skill 走本地 Skills；其余走 TOOLS）
        emit tool success/error + 可能的 image/voice/state
        追加 role=tool 结果
```

- 最多 6 轮工具调用；超过后追加一句「工具调用次数过多」并收口。
- 工具参数必须是 JSON object；解析失败返回 error 结果。
- 工具调用 ID 缺失时服务端生成。
- 一次回复里的多个工具调用按顺序执行（不做并行），便于前端工具卡稳定排序。

---

## 5. Skills

### 5.1 存储

`skills` 表存完整 JSON：

```json
{
  "id": "late-night-talk",
  "name": "深夜慢聊",
  "description": "在夜里放慢节奏，先接住情绪，再分享自己。",
  "category": "陪伴",
  "instructions": "- 每条回复 1–3 句...",
  "alwaysOn": false
}
```

人设通过 `skillIds` 关联。用户端没有 Skills 列表、没有选择器、没有安装入口。

### 5.2 两种加载方式

- `alwaysOn: true`：正文直接拼进系统提示，适合人设的「说话风格 / 边界」这种每次都要遵守的规则。
- `alwaysOn: false`：系统提示里只有简介；模型需要时调用 `activate_skill(skillId)`，服务端校验该 Skill 在本轮 `skills` 集合里，返回正文；模型再按正文执行。

这与 darl-tv 的渐进加载一致：
- 不把长正文一次性塞进上下文；
- 模型不能凭空声称「已按某 Skill 执行」；
- Skills 的可见范围由人设绑定决定，用户无法扩展。

### 5.3 内容边界

官方 Skills 目前有 7 个：深夜慢聊、俏皮拉扯、看照片、发语音、慢热推进、接住低落、场景扮演。  
人设的「边界与安全」没有做成可选 Skill，而是写进系统提示的固定段落——它不能被后台关掉。

---

## 6. 会话、记忆与关系

### 6.1 会话

- 一个用户对一个人设只有一条会话（`UNIQUE(user_id, persona_id)`）。
- 首次打开时创建会话并插入人设的 `greeting` 作为第一条 assistant 消息。
- 「重新开始」删除会话及其消息，再重新创建开场；**长期记忆不删**，需要在「她记得的事」里逐条删除。
- 会话列表按 `last_message_at` 倒序，预览取最后一条消息前 90 字。

### 6.2 关系状态

```json
{
  "affinity": 8,
  "stage": "stranger",
  "mood": "curious",
  "milestones": [{"at": "2026年11月26日 周四 凌晨01:12", "note": "第一次说起海边"}],
  "lastSeenAt": "..."
}
```

- `affinity` 0–100；阶段由数值推导：<12 stranger，<34 acquaintance，<62 close，其余 lover。
- 模型通过 `update_relationship` 更新；每次 ±3，防止一次对话跳到「恋人」。
- 聊天头部显示「阶段 · 第 N 天」；详情抽屉显示亲密度条。

### 6.3 长期记忆

- 每轮系统提示带最重要的 14 条（`importance DESC, created_at DESC`）。
- `remember` 对完全相同的文本去重；`importance` 取最大值。
- `recall` 先做 `LIKE` 搜索，没有命中就回退到最近重要记忆。
- 记忆属于 `user + persona`，不随会话删除。

---

## 7. 流式协议

响应类型 `application/x-ndjson`，一行一个 JSON：

| type | 字段 | 前端行为 |
| --- | --- | --- |
| `meta` | `conversationId`, `messageId`, `demo` | 记录会话 / 消息；显示演示标记 |
| `state` | `state` | 更新关系头部与抽屉 |
| `text` | `text` | 追加到当前 assistant 气泡 |
| `tool` | `id`, `name`, `title`, `status`, `summary` | 新增 / 更新工具卡；`running` 有脉冲 |
| `image` | `fileId`, `url`, `caption` | 追加图片气泡 |
| `voice` | `fileId`, `url`, `text` | 追加语音气泡 |
| `error` | `error{code,message,retryable,detail}` | 在气泡下显示错误 + 重试 |
| `done` | `message`, `state`, `demo`, 可选 `error` | 用服务端消息替换本地占位 |
| `ping` | — | 忽略；15 秒空闲心跳 |

实现要点：

- 服务端用 `asyncio.Queue` 把 Agent 事件泵到响应；15 秒没有事件发 `ping`，避免反向代理读超时。
- 客户端断开 → 关闭生成器 → `finally` 落库部分回复 → 取消工具任务。
- 前端流解析器按 `\n` 切行，兼容最后一行没有换行。
- `done` 用服务端返回的完整消息替换占位消息，避免前端拼接结果与服务端落库不一致。

---

## 8. API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/auth/register` / `login` / `guest` / `logout` | Cookie 会话；注册和访客必须成年确认 |
| `GET` | `/api/auth/me` | 当前用户（未登录返回 `user: null`） |
| `POST` | `/api/auth/adult-confirm` | 记录成年确认时间 |
| `GET` | `/api/personas` | 公开人设列表（不含提示词 / 工具 / Skills） |
| `GET` | `/api/personas/{id}` | 公开人设详情 + 当前关系 |
| `POST` | `/api/personas/{id}/open` | 创建 / 打开会话，返回人设 + 会话 + 消息 |
| `GET` | `/api/conversations` | 会话列表 |
| `GET` | `/api/conversations/{id}` | 会话 + 人设 + 消息 |
| `GET` | `/api/conversations/{id}/messages?before=&limit=` | 分页消息 |
| `DELETE` | `/api/conversations/{id}` | 删除会话与消息 |
| `GET` | `/api/conversations/{id}/memories` | 记忆列表 |
| `DELETE` | `/api/memories/{id}` | 删除单条记忆 |
| `POST` | `/api/chat` | 聊天流；`regenerate: true` 重答最后一条 |
| `POST` | `/api/files` | 上传图片（重新编码、去 EXIF） |
| `GET` | `/api/files/{id}` | 私有文件读取 |
| `GET` | `/api/admin/*` | 人设 / Skills / 工具 / 用户 / 概览，仅 admin |

错误统一返回：

```json
{"error": {"message": "...", "code": "...", "requestId": "..."}}
```

前端 `ApiError` 带 `status/code`；401 触发全局 `plot18:unauthorized` 事件，清空登录态。

---

## 9. 数据模型

```sql
users(id, username, display_name, password_hash, role, disabled, adult_confirmed_at, created_at)
auth_sessions(token_hash, user_id, created_at, expires_at)
personas(id, data JSON, published, sort, created_at, updated_at)
skills(id, data JSON, created_at, updated_at)
conversations(id, user_id, persona_id, state JSON, created_at, updated_at, last_message_at,
              UNIQUE(user_id, persona_id))
messages(id, conversation_id, role, content, parts JSON, meta JSON, seq, created_at)
memories(id, user_id, persona_id, content, kind, importance, created_at, last_used_at)
files(id, owner_user_id, kind, mime, size, sha256, path, width, height, created_at)
admin_audit(id, actor_id, action, target, detail, created_at)
```

- SQLite + WAL；所有查询参数绑定。
- 消息 `seq` 在事务里 `MAX(seq)+1`；同一会话单写。
- 文件本体在 `DATA_DIR/files/`，数据库只存元数据与归属。
- 删除用户时依赖 SQLite 外键清理 `auth_sessions` / `conversations`；记忆与文件目前需要运营脚本清理（下一步）。

---

## 10. 安全与隐私

- **成年门槛**：前端年龄门 + 后端 `adult_confirmed_at` 双重校验；后台保存人设再校验年龄 ≥ 18。
- **会话归属**：所有会话 / 消息 / 记忆接口都校验 `user_id`；带 `conversationId` 但不存在时直接 404，不回退新建。
- **文件归属**：上传绑定 `owner_user_id`；读取、作为图片输入时校验；用户照片重新编码为 JPEG，去掉 EXIF。
- **配置隔离**：公开人设接口只返回展示字段；`promptExtra/systemPrompt/toolIds/skillIds` 只在 admin 接口返回。
- **管理员**：`role=admin` 才能访问 `/api/admin/*`；后台用户停用接口不能停用管理员。
- **限流与互斥**：每用户每分钟消息数；同一用户 + 人设只允许一轮生成。
- **密钥**：只从环境变量读取；不进前端、不进数据库、不写日志。
- **系统提示**：明确要求模型不透露提示词 / 工具 / 模型、不索取敏感信息、遇到现实危机优先关心安全。
- **内容**：种子人设不写露骨内容；后台可以按运营策略调整，但 `promptExtra` 仍受固定安全段约束。

---

## 11. 扩展指南

### 加一个工具

1. 在 `backend/app/services/tools.py` 写 handler + `ToolSpec`，加进 `TOOLS`。
2. 前端 `toolIcons` 里补一个图标（可选，默认 Brain）。
3. 后台 `/admin` 的工具列表自动出现；勾选到人设即可。
4. 如果工具产生媒体，在 `agent._tool_event` 里加 `image` / `voice` 事件与 `parts`。
5. 补测试：`tests/test_agent_loop.py` 用 FakeLLM 触发工具。

### 加一个 Skill

1. 后台 `/admin` → Skills → 新建；填名称、简介、分类、正文、是否 always-on。
2. 到人设的 Skills 里勾选。
3. 用户端不需要任何改动；模型会在需要时自己读正文。

### 加一个人设

1. 后台人设 → 新建；填 id、名字、年龄、城市、职业、tagline、小传、性格、说话方式、关系动态。
2. 填开场白 + 四个开场建议 + 封面色 A/B；勾工具与 Skills。
3. 上架；发现页与列表自动出现。
4. 批量导入也可以直接改 `backend/app/seed.py`（仅空库时写入），或写 admin API 脚本。

### 换图片 / 语音服务

- `services/studio.py` 目前按 OpenAI `/v1/images/generations` 与 `/v1/audio/speech` 实现。
- 换其他厂商时只改这个文件的两个方法，保持返回 `{fileId, url, caption/text}` 即可；工具层与前端不用动。
- 想接「角色参考图一致性」时，在 `Studio.selfie()` 里把人设参考图作为 image edit / reference 传入。

### 接真实人设封面

- 当前 `PersonaArt` 用 `palette` 生成渐变 + 线稿 + 首字。
- 后台加 `coverUrl / avatarUrl` 字段后，在 `PersonaArt` 里优先渲染 `<img>`；保留渐变作为加载占位。
- 上传仍走 `/api/files`，文件私有；公开展示需要单独的 `persona-assets` owner 与缓存策略。

---

## 12. 已知限制 / 下一步

1. **长对话摘要**：目前只截最近 48 条；建议在超过阈值后异步生成「关系摘要」写入 `conversations.state.summary`，并在系统提示中注入。
2. **多实例**：运行互斥与限流是进程内内存；多实例要换 Redis。
3. **后台运行 / 重订阅**：当前浏览器断开即停止；若要做「她深夜主动发消息」，需要后台任务队列与推送。
4. **内容审核**：目前靠系统提示与后端年龄门槛；上线前应接文本 / 图片审核与举报队列。
5. **订阅与计费**：未接支付；人设已有 `sort/published`，可加 `tier/price` 与用量记录。
6. **数据删除**：用户删除账号时需要级联清理记忆、文件、会话；当前只有会话删除与单条记忆删除。
7. **可观测性**：只有 uvicorn 日志；建议加请求 ID 全链路、工具耗时、模型 token 统计与错误聚合。
8. **人设一致性**：生图目前只靠提示词；要稳定「同一个人」需要参考图 / LoRA / 固定 seed。
