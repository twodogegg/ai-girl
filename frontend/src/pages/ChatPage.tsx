import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, BookOpen, Brain, RotateCcw, Trash2, UserRound } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useApp } from "@/context/AppContext";
import { useChat, type ChatInitial } from "@/hooks/useChat";
import { deleteConversation, deleteMemory, listMemories, openPersona } from "@/api/personas";
import { ChatHeader } from "@/components/ChatHeader";
import { MessageList } from "@/components/MessageList";
import { Composer } from "@/components/Composer";
import { PersonaSheet } from "@/components/PersonaSheet";
import { Sheet } from "@/components/Sheet";
import { PersonaAvatar } from "@/components/PersonaArt";

type Memory = { id: string; content: string; kind: string; created_at: string };

function ChatRoom({ initial }: { initial: ChatInitial }) {
  const navigate = useNavigate();
  const { toast } = useApp();
  const [moreOpen, setMoreOpen] = useState(false);
  const [infoOpen, setInfoOpen] = useState(false);
  const [memoriesOpen, setMemoriesOpen] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [memoryLoading, setMemoryLoading] = useState(false);

  const chat = useChat(initial, () => window.dispatchEvent(new Event("plot18:conversations-changed")));

  useEffect(() => {
    if (chat.notice) toast(chat.notice);
  }, [chat.notice, toast]);

  useEffect(() => {
    if (!memoriesOpen) return;
    setMemoryLoading(true);
    listMemories(chat.conversation.id)
      .then(setMemories)
      .catch(() => setMemories([]))
      .finally(() => setMemoryLoading(false));
  }, [memoriesOpen, chat.conversation.id]);

  const reset = async () => {
    setConfirmReset(false);
    setMoreOpen(false);
    try {
      await deleteConversation(chat.conversation.id);
      const data = await openPersona(chat.persona.id);
      chat.load(data);
      toast("这段对话重新开始了，她说过会记得的事还留着。");
    } catch (error) {
      toast(error instanceof Error ? error.message : "操作失败。");
    }
  };

  const stage = chat.persona.relationshipState;
  const placeholder = chat.sending ? "她正在回复…" : chat.uploading ? "照片正在上传…" : "说点什么…";

  return (
    <div className="chat-page">
      <ChatHeader
        persona={chat.persona}
        demo={chat.demo}
        onBack={() => navigate("/")}
        onMore={() => setMoreOpen(true)}
      />

      {chat.demo && (
        <div className="demo-banner">
          演示模式：尚未配置文本模型，当前回复由本地演示引擎生成。
        </div>
      )}

      <MessageList
        messages={chat.messages}
        persona={chat.persona}
        onRetry={() => void chat.regenerate()}
        starters={chat.persona.starters}
        onStarter={(text) => void chat.send(text)}
      />

      <Composer
        sending={chat.sending}
        uploading={chat.uploading}
        onSend={chat.send}
        onStop={chat.stop}
        placeholder={placeholder}
      />

      <Sheet open={moreOpen} onClose={() => setMoreOpen(false)} title="这段关系">
        <div className="relation-card">
          <PersonaAvatar persona={chat.persona} size={54} />
          <div>
            <strong>{chat.persona.nameZh || chat.persona.name}</strong>
            <p>{stage ? `第 ${stage.daysKnown} 天 · ${stage.stage === "lover" ? "亲密" : stage.stage === "close" ? "暧昧" : stage.stage === "acquaintance" ? "开始熟悉" : "刚刚认识"}` : "刚刚认识"}</p>
          </div>
          <span className="relation-card__score">{stage?.affinity ?? 0}</span>
        </div>
        <div className="sheet-actions">
          <button type="button" className="sheet-action" onClick={() => { setMoreOpen(false); setInfoOpen(true); }}>
            <UserRound size={18} /><span>关于她</span>
          </button>
          <button type="button" className="sheet-action" onClick={() => { setMoreOpen(false); setMemoriesOpen(true); }}>
            <BookOpen size={18} /><span>她记得的事</span><small>{memories.length || ""}</small>
          </button>
          <button type="button" className="sheet-action sheet-action--danger" onClick={() => { setMoreOpen(false); setConfirmReset(true); }}>
            <RotateCcw size={18} /><span>重新开始这段对话</span>
          </button>
        </div>
        <p className="sheet-fine">重新开始只会清空聊天记录，长期记忆仍会保留；你可以在「她记得的事」里逐条删除。</p>
      </Sheet>

      <Sheet open={confirmReset} onClose={() => setConfirmReset(false)} title="重新开始？">
        <p className="sheet-copy">
          这会把你们的聊天记录清空，并回到她的第一句开场白。她记得的长期记忆不会自动删除。
        </p>
        <div className="sheet-buttons">
          <button type="button" className="button soft-button" onClick={() => setConfirmReset(false)}>再想想</button>
          <button type="button" className="button button--danger" onClick={() => void reset()}>重新开始</button>
        </div>
      </Sheet>

      <Sheet open={memoriesOpen} onClose={() => setMemoriesOpen(false)} title="她记得的事">
        {memoryLoading ? (
          <p className="muted">正在翻开她的记忆…</p>
        ) : memories.length === 0 ? (
          <div className="empty-state empty-state--compact">
            <Brain size={24} strokeWidth={1.4} />
            <p>她还没有记住什么。多聊几句，她会慢慢记住你。</p>
          </div>
        ) : (
          <div className="memory-list">
            {memories.map((memory) => (
              <div key={memory.id} className="memory-item">
                <div>
                  <span className="memory-item__kind">{memory.kind}</span>
                  <p>{memory.content}</p>
                </div>
                <button
                  type="button"
                  className="icon-button"
                  aria-label="删除这条记忆"
                  onClick={async () => {
                    await deleteMemory(memory.id);
                    setMemories((current) => current.filter((item) => item.id !== memory.id));
                    toast("她已经忘了这件事。");
                  }}
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>
        )}
        <p className="sheet-fine">记忆只对你和她（也就是这段对话）可见。删除后不可恢复。</p>
      </Sheet>

      <PersonaSheet
        persona={infoOpen ? chat.persona : null}
        onClose={() => setInfoOpen(false)}
        onStart={() => setInfoOpen(false)}
      />
    </div>
  );
}

export function ChatPage() {
  const { personaId = "" } = useParams();
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [initial, setInitial] = useState<ChatInitial | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      navigate(`/login?next=${encodeURIComponent(`/chat/${personaId}`)}`, { replace: true });
      return;
    }
    let cancelled = false;
    setLoading(true);
    openPersona(personaId)
      .then((data) => { if (!cancelled) setInitial(data); })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : "这段对话暂时打不开。"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [authLoading, navigate, personaId, user]);

  if (loading || authLoading) {
    return (
      <div className="chat-page chat-page--loading">
        <div className="chat-loading">
          <span className="eyebrow">CONNECTING</span>
          <p>正在接通这条线…</p>
        </div>
      </div>
    );
  }

  if (error || !initial) {
    return (
      <div className="chat-page">
        <header className="chat-header">
          <button type="button" className="icon-button" aria-label="返回" onClick={() => navigate("/")}>
            <ArrowLeft size={20} />
          </button>
          <div className="chat-header__text"><div className="chat-header__name">这条线没有接通</div></div>
        </header>
        <div className="empty-state empty-state--card">
          <h3>{error || "找不到这个人设。"}</h3>
          <p>回到发现页，换一个她试试。</p>
          <button type="button" className="button button--primary" onClick={() => navigate("/")}>回到发现</button>
        </div>
      </div>
    );
  }

  return <ChatRoom key={initial.persona.id} initial={initial} />;
}
