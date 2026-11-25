import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { MessageCircle } from "lucide-react";
import type { Conversation } from "@/types";
import { useAuth } from "@/context/AuthContext";
import { listConversations } from "@/api/personas";
import { PersonaAvatar } from "@/components/PersonaArt";

function when(value: string) {
  const diff = Date.now() - new Date(value).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} 天前`;
  return new Date(value).toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" });
}

export function Chats() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    if (!user) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    listConversations()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
    const handler = () => refresh();
    window.addEventListener("plot18:conversations-changed", handler);
    window.addEventListener("focus", handler);
    return () => {
      window.removeEventListener("plot18:conversations-changed", handler);
      window.removeEventListener("focus", handler);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  return (
    <div className="page chats">
      <header className="page-head">
        <span className="eyebrow">YOUR CONVERSATIONS</span>
        <h1>消息</h1>
        <p>那些没说完的话，都还在这里。</p>
      </header>

      {!user ? (
        <div className="empty-state empty-state--card">
          <MessageCircle size={28} strokeWidth={1.4} />
          <h3>还没有属于你的对话</h3>
          <p>登录或直接以访客身份进入，选一个她开始。</p>
          <Link className="button button--primary" to="/login?next=/chats">进入夜色</Link>
        </div>
      ) : loading ? (
        <div className="chat-list">
          {Array.from({ length: 4 }).map((_, index) => <div key={index} className="chat-row chat-row--skeleton" />)}
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state empty-state--card">
          <MessageCircle size={28} strokeWidth={1.4} />
          <h3>还没有开始</h3>
          <p>去看看今晚谁在线。第一句话不用想太久。</p>
          <Link className="button button--primary" to="/">去发现</Link>
        </div>
      ) : (
        <div className="chat-list">
          {items.map((item) => {
            const persona = item.persona;
            if (!persona) return null;
            return (
              <button key={item.id} type="button" className="chat-row" onClick={() => navigate(`/chat/${item.personaId}`)}>
                <PersonaAvatar persona={persona} size={52} />
                <div className="chat-row__body">
                  <div className="chat-row__top">
                    <strong>{persona.nameZh || persona.name}</strong>
                    <span>{when(item.lastMessageAt)}</span>
                  </div>
                  <p>{item.preview || persona.tagline || "她还在等你开口。"}</p>
                </div>
                <span className="chat-row__stage">{item.state.stage === "lover" ? "亲密" : item.state.stage === "close" ? "暧昧" : ""}</span>
              </button>
            );
          })}
        </div>
      )}
      <footer className="page-foot">
        <span>对话会保存在你的账号里</span>
        <span><Link to="/me">管理记忆与设置</Link></span>
      </footer>
    </div>
  );
}
