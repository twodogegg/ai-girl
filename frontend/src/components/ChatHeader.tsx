import { ChevronLeft, MoreHorizontal } from "lucide-react";
import type { Persona } from "@/types";
import { PersonaAvatar } from "./PersonaArt";

const stageLabel: Record<string, string> = {
  stranger: "刚刚认识",
  acquaintance: "开始熟悉",
  close: "有点暧昧",
  lover: "亲密",
};

export function ChatHeader({ persona, demo, onBack, onMore }: {
  persona: Persona;
  demo: boolean;
  onBack: () => void;
  onMore: () => void;
}) {
  const state = persona.relationshipState;
  return (
    <header className="chat-header">
      <button type="button" className="icon-button chat-header__back" aria-label="返回" onClick={onBack}>
        <ChevronLeft size={22} />
      </button>
      <PersonaAvatar persona={persona} size={36} />
      <div className="chat-header__text">
        <div className="chat-header__name">
          {persona.nameZh || persona.name}
          {demo && <span className="demo-badge">演示</span>}
        </div>
        <div className="chat-header__status">
          <span className="online-dot" />
          {state ? `${stageLabel[state.stage] || state.stage} · 第 ${state.daysKnown} 天` : "在线"}
        </div>
      </div>
      <button type="button" className="icon-button" aria-label="更多" onClick={onMore}>
        <MoreHorizontal size={21} />
      </button>
    </header>
  );
}
