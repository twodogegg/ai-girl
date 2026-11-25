import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, X } from "lucide-react";
import type { ChatMessage, Persona } from "@/types";
import { MessageBubble } from "./MessageBubble";

type Props = {
  messages: ChatMessage[];
  persona: Persona;
  onRetry: () => void;
  starters?: string[];
  onStarter?: (text: string) => void;
};

function dayLabel(value: string) {
  const date = new Date(value);
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const days = Math.round((start - target) / 86400000);
  if (days === 0) return "今天";
  if (days === 1) return "昨天";
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日`;
}

export function MessageList({ messages, persona, onRetry, starters, onStarter }: Props) {
  const container = useRef<HTMLDivElement | null>(null);
  const bottom = useRef<HTMLDivElement | null>(null);
  const [atBottom, setAtBottom] = useState(true);
  const [lightbox, setLightbox] = useState<string | null>(null);

  const groups = useMemo(() => {
    const result: Array<{ label: string; items: Array<{ message: ChatMessage; previousRole?: string }> }> = [];
    for (const message of messages) {
      const label = dayLabel(message.createdAt);
      const last = result[result.length - 1];
      if (!last || last.label !== label) result.push({ label, items: [{ message }] });
      else last.items.push({ message, previousRole: last.items[last.items.length - 1]?.message.role });
    }
    return result;
  }, [messages]);

  useEffect(() => {
    if (atBottom) bottom.current?.scrollIntoView({ block: "end" });
  }, [messages, atBottom]);

  const onScroll = () => {
    const element = container.current;
    if (!element) return;
    setAtBottom(element.scrollHeight - element.scrollTop - element.clientHeight < 140);
  };

  return (
    <div className="message-list" ref={container} onScroll={onScroll}>
      <div className="message-list__inner">
        <div className="chat-intro">
          <span className="eyebrow">A PRIVATE LINE</span>
          <p>你们的对话只属于这里。她记得重要的事，也会慢慢更了解你。</p>
        </div>
        {groups.map((group) => (
          <section key={group.label}>
            <div className="day-divider"><span>{group.label}</span></div>
            {group.items.map(({ message, previousRole }) => (
              <MessageBubble
                key={message.id}
                message={message}
                persona={persona}
                previousRole={previousRole}
                onRetry={onRetry}
                onImage={setLightbox}
              />
            ))}
          </section>
        ))}
        {messages.length <= 1 && starters && starters.length > 0 && (
          <div className="chat-starters">
            {starters.map((starter) => (
              <button key={starter} type="button" className="starter-chip" onClick={() => onStarter?.(starter)}>
                {starter}
              </button>
            ))}
          </div>
        )}
        <div ref={bottom} />
      </div>
      {!atBottom && (
        <button type="button" className="scroll-latest" onClick={() => { setAtBottom(true); bottom.current?.scrollIntoView({ behavior: "smooth" }); }}>
          <ChevronDown size={16} /> 回到最新
        </button>
      )}
      {lightbox && (
        <div className="lightbox" role="dialog" aria-modal="true" onClick={() => setLightbox(null)}>
          <button type="button" className="lightbox__close" aria-label="关闭" onClick={() => setLightbox(null)}>
            <X size={20} />
          </button>
          <img src={lightbox} alt="照片" onClick={(event) => event.stopPropagation()} />
        </div>
      )}
    </div>
  );
}
