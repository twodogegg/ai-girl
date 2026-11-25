import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Plus, Save, Trash2 } from "lucide-react";
import type { AdminPersona, AdminSkill, AdminTool } from "@/types";
import { useAuth } from "@/context/AuthContext";
import { useApp } from "@/context/AppContext";
import { PersonaArt } from "@/components/PersonaArt";
import {
  createPersona, deletePersona, deleteSkill, getAdminPersonas, getAdminSkills, getOverview, getTools, getUsers,
  saveSkill, setUserDisabled, updatePersona, type AdminUser, type Overview,
} from "@/api/admin";

type Tab = "overview" | "personas" | "skills";

const emptyPersona = (): AdminPersona => ({
  id: `persona-${Date.now().toString(36)}`,
  name: "",
  nameZh: "",
  age: 24,
  city: "",
  occupation: "",
  tagline: "",
  bio: "",
  personality: "",
  speakingStyle: "",
  relationship: "",
  languages: ["中文"],
  tags: [],
  palette: ["#3a2a1e", "#c9974c"],
  greeting: "",
  starters: [],
  online: true,
  published: true,
  toolIds: ["remember", "recall", "update_relationship", "get_time"],
  skillIds: [],
  promptExtra: "",
  systemPrompt: "",
  temperature: 0.85,
  sort: 999,
  timezone: "Asia/Shanghai",
  voice: "",
});

const emptySkill = (): AdminSkill => ({
  id: "",
  name: "",
  description: "",
  category: "自定义",
  instructions: "",
  alwaysOn: false,
});

const toLines = (items: string[]) => items.join("\n");
const fromLines = (value: string) => value.split("\n").map((item) => item.trim()).filter(Boolean);
const toComma = (items: string[]) => items.join("、");
const fromComma = (value: string) => value.split(/[、,，]/).map((item) => item.trim()).filter(Boolean);

export function Admin() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const { toast } = useApp();
  const [tab, setTab] = useState<Tab>("overview");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [personas, setPersonas] = useState<AdminPersona[]>([]);
  const [skills, setSkills] = useState<AdminSkill[]>([]);
  const [tools, setTools] = useState<AdminTool[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [draft, setDraft] = useState<AdminPersona | null>(null);
  const [skillDraft, setSkillDraft] = useState<AdminSkill | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const [list, skillList, toolList, data, userList] = await Promise.all([
        getAdminPersonas(), getAdminSkills(), getTools(), getOverview(), getUsers(),
      ]);
      setPersonas(list);
      setSkills(skillList);
      setTools(toolList);
      setOverview(data);
      setUsers(userList);
      if (!selectedId && list.length) {
        setSelectedId(list[0].id);
        setDraft(structuredClone(list[0]));
      }
    } catch (error) {
      toast(error instanceof Error ? error.message : "后台加载失败。");
    }
  };

  useEffect(() => {
    if (!loading && user?.role === "admin") void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, user?.role]);

  useEffect(() => {
    if (!loading && !user) navigate("/login?next=/admin", { replace: true });
  }, [loading, navigate, user]);

  const isNew = useMemo(() => Boolean(draft && !personas.some((item) => item.id === draft.id)), [draft, personas]);

  const focusEditor = () => {
    if (window.innerWidth < 900) {
      window.setTimeout(() => {
        document.querySelector(".admin-editor")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 60);
    }
  };

  const selectPersona = (persona: AdminPersona) => {
    setSelectedId(persona.id);
    setDraft(structuredClone(persona));
    focusEditor();
  };

  const startNewPersona = () => {
    const next = emptyPersona();
    setSelectedId(next.id);
    setDraft(next);
    setTab("personas");
    focusEditor();
  };

  const savePersonaDraft = async () => {
    if (!draft || busy) return;
    setBusy(true);
    try {
      const saved = isNew ? await createPersona(draft) : await updatePersona(draft);
      const list = await getAdminPersonas();
      setPersonas(list);
      setSelectedId(saved.id);
      setDraft(structuredClone(saved));
      toast("人设已保存。");
    } catch (error) {
      toast(error instanceof Error ? error.message : "保存失败。");
    } finally {
      setBusy(false);
    }
  };

  const removePersona = async () => {
    if (!draft || busy) return;
    if (!window.confirm(`确定删除「${draft.name || draft.id}」？这会同时删除相关会话入口，但不会删除用户消息。`)) return;
    setBusy(true);
    try {
      await deletePersona(draft.id);
      const list = await getAdminPersonas();
      setPersonas(list);
      setSelectedId(list[0]?.id || "");
      setDraft(list[0] ? structuredClone(list[0]) : null);
      toast("人设已删除。");
    } catch (error) {
      toast(error instanceof Error ? error.message : "删除失败。");
    } finally {
      setBusy(false);
    }
  };

  const saveSkillDraft = async () => {
    if (!skillDraft || busy) return;
    setBusy(true);
    try {
      const saved = await saveSkill(skillDraft);
      const list = await getAdminSkills();
      setSkills(list);
      setSkillDraft(structuredClone(saved));
      toast("Skill 已保存。");
    } catch (error) {
      toast(error instanceof Error ? error.message : "保存失败。");
    } finally {
      setBusy(false);
    }
  };

  const removeSkill = async () => {
    if (!skillDraft?.id || busy) return;
    if (!window.confirm(`确定删除 Skill「${skillDraft.name}」？已绑定它的人设会失去这个 Skill。`)) return;
    setBusy(true);
    try {
      await deleteSkill(skillDraft.id);
      const list = await getAdminSkills();
      setSkills(list);
      setSkillDraft(list[0] ? structuredClone(list[0]) : null);
      toast("Skill 已删除。");
    } catch (error) {
      toast(error instanceof Error ? error.message : "删除失败。");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <div className="admin-page admin-page--center">正在进入后台…</div>;
  if (!user || user.role !== "admin") {
    return (
      <div className="admin-page admin-page--center">
        <div className="empty-state empty-state--card">
          <h2>这里只对主理人开放</h2>
          <p>请使用管理员账号登录。</p>
          <Link className="button button--primary" to="/login?next=/admin">去登录</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-page">
      <header className="admin-top">
        <Link to="/me" className="icon-button" aria-label="返回"><ArrowLeft size={19} /></Link>
        <span className="wordmark">plot<span>.</span>18 <em>console</em></span>
        <span className="admin-top__user">{user.displayName}</span>
      </header>

      <nav className="admin-tabs">
        {(["overview", "personas", "skills"] as Tab[]).map((item) => (
          <button key={item} type="button" className={tab === item ? "is-active" : ""} onClick={() => setTab(item)}>
            {item === "overview" ? "概览" : item === "personas" ? "人设" : "Skills"}
          </button>
        ))}
      </nav>

      {tab === "overview" && overview && (
        <main className="admin-overview">
          <div className="stat-grid">
            {Object.entries(overview.counts).map(([key, value]) => (
              <div key={key} className="stat-card">
                <span>{({ users: "用户", conversations: "对话", messages: "消息", personas: "人设", skills: "Skills", memories: "记忆" } as Record<string, string>)[key] || key}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
          <section className="admin-panel">
            <h2>最近的对话</h2>
            {overview.recent.length === 0 ? <p className="muted">还没有人开始。</p> : (
              <div className="admin-table">
                {overview.recent.map((row) => (
                  <div key={row.id} className="admin-table__row">
                    <span>{row.displayName}</span>
                    <span>{row.personaName}</span>
                    <span className="muted">{new Date(row.lastMessageAt).toLocaleString("zh-CN")}</span>
                  </div>
                ))}
              </div>
            )}
          </section>
          <section className="admin-panel">
            <h2>用户</h2>
            <div className="admin-table">
              {users.map((row) => (
                <div key={row.id} className="admin-table__row admin-table__row--user">
                  <span>{row.displayName} <small>@{row.username}</small></span>
                  <span>{row.role === "admin" ? "管理员" : row.adultConfirmed ? "成年已确认" : "未确认"}</span>
                  <button
                    type="button"
                    className="soft-button"
                    disabled={row.role === "admin"}
                    onClick={async () => {
                      await setUserDisabled(row.id, !row.disabled);
                      setUsers((current) => current.map((item) => item.id === row.id ? { ...item, disabled: !item.disabled } : item));
                      toast(row.disabled ? "用户已恢复。" : "用户已停用。");
                    }}
                  >
                    {row.disabled ? "恢复" : "停用"}
                  </button>
                </div>
              ))}
            </div>
          </section>
        </main>
      )}

      {tab === "personas" && (
        <main className="admin-split">
          <aside className="admin-list">
            <button type="button" className="button button--primary button--full" onClick={startNewPersona}>
              <Plus size={16} /> 新建人设
            </button>
            {personas.map((persona) => (
              <button
                key={persona.id}
                type="button"
                className={`admin-list__item${selectedId === persona.id ? " is-active" : ""}`}
                onClick={() => selectPersona(persona)}
              >
                <span className="admin-list__art"><PersonaArt persona={persona} variant="thumb" /></span>
                <span>
                  <strong>{persona.nameZh || persona.name || "未命名"}</strong>
                  <small>{persona.id}</small>
                </span>
                <i className={persona.published ? "is-live" : ""}>{persona.published ? "已上架" : "草稿"}</i>
              </button>
            ))}
          </aside>

          {draft ? (
            <section className="admin-editor">
              <div className="admin-editor__head">
                <div>
                  <h1>{draft.nameZh || draft.name || "新的她"}</h1>
                  <p>{isNew ? "尚未保存" : `id：${draft.id}`}</p>
                </div>
                <div className="admin-editor__actions">
                  {!isNew && <button type="button" className="icon-button" aria-label="删除" onClick={() => void removePersona()}><Trash2 size={17} /></button>}
                  <button type="button" className="button button--primary" disabled={busy} onClick={() => void savePersonaDraft()}>
                    <Save size={15} /> {busy ? "保存中…" : "保存"}
                  </button>
                </div>
              </div>

              <div className="admin-preview">
                <div className="admin-preview__art"><PersonaArt persona={draft} variant="hero" /></div>
                <div>
                  <span className="eyebrow">LIVE PREVIEW</span>
                  <h2>{draft.nameZh || draft.name || "她的名字"}</h2>
                  <p>{draft.tagline || "一句让人记住她的话。"}</p>
                  <small>{draft.age} 岁 · {draft.city || "城市"} · {draft.occupation || "职业"}</small>
                </div>
              </div>

              <div className="form-section">
                <h3>基本</h3>
                <div className="form-grid">
                  <label className="field"><span>人设 ID</span><input value={draft.id} disabled={!isNew} onChange={(event) => setDraft({ ...draft, id: event.target.value })} /></label>
                  <label className="field"><span>英文名</span><input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label>
                  <label className="field"><span>中文名</span><input value={draft.nameZh} onChange={(event) => setDraft({ ...draft, nameZh: event.target.value })} /></label>
                  <label className="field"><span>年龄（18+）</span><input type="number" min={20} max={60} value={draft.age} onChange={(event) => setDraft({ ...draft, age: Number(event.target.value) })} /></label>
                  <label className="field"><span>城市</span><input value={draft.city} onChange={(event) => setDraft({ ...draft, city: event.target.value })} /></label>
                  <label className="field"><span>职业</span><input value={draft.occupation} onChange={(event) => setDraft({ ...draft, occupation: event.target.value })} /></label>
                  <label className="field field--wide"><span>一句话介绍</span><input value={draft.tagline} onChange={(event) => setDraft({ ...draft, tagline: event.target.value })} /></label>
                  <label className="field"><span>标签（顿号分隔）</span><input value={toComma(draft.tags)} onChange={(event) => setDraft({ ...draft, tags: fromComma(event.target.value) })} /></label>
                  <label className="field"><span>语言（顿号分隔）</span><input value={toComma(draft.languages)} onChange={(event) => setDraft({ ...draft, languages: fromComma(event.target.value) })} /></label>
                </div>
              </div>

              <div className="form-section">
                <h3>人设与说话方式</h3>
                <label className="field"><span>小传</span><textarea rows={3} value={draft.bio} onChange={(event) => setDraft({ ...draft, bio: event.target.value })} /></label>
                <label className="field"><span>性格</span><textarea rows={2} value={draft.personality} onChange={(event) => setDraft({ ...draft, personality: event.target.value })} /></label>
                <label className="field"><span>说话方式</span><textarea rows={2} value={draft.speakingStyle} onChange={(event) => setDraft({ ...draft, speakingStyle: event.target.value })} /></label>
                <label className="field"><span>关系动态</span><textarea rows={2} value={draft.relationship} onChange={(event) => setDraft({ ...draft, relationship: event.target.value })} /></label>
                <label className="field"><span>补充设定（会拼进系统提示）</span><textarea rows={3} value={draft.promptExtra || ""} onChange={(event) => setDraft({ ...draft, promptExtra: event.target.value })} /></label>
                <label className="field"><span>完全覆盖提示词（高级，留空则用上面的字段自动拼装）</span><textarea rows={4} value={draft.systemPrompt || ""} onChange={(event) => setDraft({ ...draft, systemPrompt: event.target.value })} /></label>
              </div>

              <div className="form-section">
                <h3>开场与外观</h3>
                <label className="field"><span>她的第一句话</span><textarea rows={2} value={draft.greeting} onChange={(event) => setDraft({ ...draft, greeting: event.target.value })} /></label>
                <label className="field"><span>开场建议（每行一句，最多 4 句）</span><textarea rows={3} value={toLines(draft.starters)} onChange={(event) => setDraft({ ...draft, starters: fromLines(event.target.value).slice(0, 4) })} /></label>
                <div className="form-grid">
                  <label className="field"><span>封面色 A</span><input type="color" value={draft.palette?.[0] ?? "#3a2a1e"} onChange={(event) => setDraft({ ...draft, palette: [event.target.value, draft.palette?.[1] ?? "#c9974c"] })} /></label>
                  <label className="field"><span>封面色 B</span><input type="color" value={draft.palette?.[1] ?? "#c9974c"} onChange={(event) => setDraft({ ...draft, palette: [draft.palette?.[0] ?? "#3a2a1e", event.target.value] })} /></label>
                  <label className="field"><span>时区</span><input value={draft.timezone || ""} onChange={(event) => setDraft({ ...draft, timezone: event.target.value })} /></label>
                  <label className="field"><span>排序（越小越前）</span><input type="number" value={draft.sort ?? 999} onChange={(event) => setDraft({ ...draft, sort: Number(event.target.value) })} /></label>
                  <label className="field"><span>语音音色（TTS voice id）</span><input value={draft.voice || ""} onChange={(event) => setDraft({ ...draft, voice: event.target.value })} placeholder="留空用全局 TTS_VOICE" /></label>
                  <label className="field"><span>模型覆盖</span><input value={draft.model || ""} onChange={(event) => setDraft({ ...draft, model: event.target.value })} placeholder="留空用全局 LLM_MODEL" /></label>
                  <label className="field"><span>温度 {draft.temperature?.toFixed(2)}</span><input type="range" min={0.3} max={1.2} step={0.01} value={draft.temperature ?? 0.85} onChange={(event) => setDraft({ ...draft, temperature: Number(event.target.value) })} /></label>
                  <label className="field field--check"><input type="checkbox" checked={draft.published} onChange={(event) => setDraft({ ...draft, published: event.target.checked })} /> 已上架</label>
                </div>
              </div>

              <div className="form-section">
                <h3>工具</h3>
                <p className="form-hint">用户看不到也选不了；只有勾选的工具会挂在这个人设的模型上。</p>
                <div className="check-grid">
                  {tools.map((tool) => (
                    <label key={tool.id} className={`check-card${tool.available ? "" : " is-off"}`}>
                      <input
                        type="checkbox"
                        checked={draft.toolIds.includes(tool.id)}
                        onChange={(event) => setDraft({
                          ...draft,
                          toolIds: event.target.checked
                            ? [...draft.toolIds, tool.id]
                            : draft.toolIds.filter((item) => item !== tool.id),
                        })}
                      />
                      <span>
                        <strong>{tool.title}</strong>
                        <small>{tool.description}</small>
                        {!tool.available && <em>当前未配置服务，调用会返回不可用</em>}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-section">
                <h3>Skills</h3>
                <p className="form-hint">勾选后，模型只能看到这些 Skill 的简介，需要时自己读取正文；用户界面不会出现 Skills。</p>
                <div className="check-grid">
                  {skills.map((skill) => (
                    <label key={skill.id} className="check-card">
                      <input
                        type="checkbox"
                        checked={draft.skillIds.includes(skill.id)}
                        onChange={(event) => setDraft({
                          ...draft,
                          skillIds: event.target.checked
                            ? [...draft.skillIds, skill.id]
                            : draft.skillIds.filter((item) => item !== skill.id),
                        })}
                      />
                      <span>
                        <strong>{skill.name}</strong>
                        <small>{skill.description}</small>
                        {skill.alwaysOn && <em>always-on：正文会直接注入</em>}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="admin-editor__footer">
                <button type="button" className="button button--primary" disabled={busy} onClick={() => void savePersonaDraft()}>
                  <Save size={15} /> {busy ? "保存中…" : "保存人设"}
                </button>
              </div>
            </section>
          ) : (
            <section className="admin-editor admin-editor--empty">选择左侧的人设开始编辑。</section>
          )}
        </main>
      )}

      {tab === "skills" && (
        <main className="admin-split">
          <aside className="admin-list">
            <button type="button" className="button button--primary button--full" onClick={() => { setSkillDraft(emptySkill()); focusEditor(); }}>
              <Plus size={16} /> 新建 Skill
            </button>
            {skills.map((skill) => (
              <button
                key={skill.id}
                type="button"
                className={`admin-list__item${skillDraft?.id === skill.id ? " is-active" : ""}`}
                onClick={() => { setSkillDraft(structuredClone(skill)); focusEditor(); }}
              >
                <span>
                  <strong>{skill.name}</strong>
                  <small>{skill.id}</small>
                </span>
                <i className={skill.alwaysOn ? "is-live" : ""}>{skill.alwaysOn ? "always-on" : "按需"}</i>
              </button>
            ))}
          </aside>

          {skillDraft ? (
            <section className="admin-editor">
              <div className="admin-editor__head">
                <div>
                  <h1>{skillDraft.name || "新的 Skill"}</h1>
                  <p>{skillDraft.id ? `id：${skillDraft.id}` : "尚未保存"}</p>
                </div>
                <div className="admin-editor__actions">
                  {skillDraft.id && <button type="button" className="icon-button" aria-label="删除" onClick={() => void removeSkill()}><Trash2 size={17} /></button>}
                  <button type="button" className="button button--primary" disabled={busy} onClick={() => void saveSkillDraft()}>
                    <Save size={15} /> {busy ? "保存中…" : "保存"}
                  </button>
                </div>
              </div>
              <div className="form-section">
                <div className="form-grid">
                  <label className="field"><span>名称</span><input value={skillDraft.name} onChange={(event) => setSkillDraft({ ...skillDraft, name: event.target.value })} /></label>
                  <label className="field"><span>分类</span><input value={skillDraft.category} onChange={(event) => setSkillDraft({ ...skillDraft, category: event.target.value })} /></label>
                  <label className="field field--wide"><span>简介（会出现在模型可见的清单里）</span><input value={skillDraft.description} onChange={(event) => setSkillDraft({ ...skillDraft, description: event.target.value })} /></label>
                  <label className="field field--check"><input type="checkbox" checked={Boolean(skillDraft.alwaysOn)} onChange={(event) => setSkillDraft({ ...skillDraft, alwaysOn: event.target.checked })} /> always-on：正文直接注入</label>
                </div>
                <label className="field">
                  <span>正文（Markdown，模型按需读取）</span>
                  <textarea
                    className="code-area"
                    rows={18}
                    value={skillDraft.instructions}
                    onChange={(event) => setSkillDraft({ ...skillDraft, instructions: event.target.value })}
                    placeholder={"- 先接住情绪\n- 每条 1–3 句\n- ..."}
                  />
                </label>
              </div>
            </section>
          ) : (
            <section className="admin-editor admin-editor--empty">选择左侧的 Skill 开始编辑。</section>
          )}
        </main>
      )}
    </div>
  );
}
