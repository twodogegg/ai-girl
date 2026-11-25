import { useEffect, useRef, useState } from "react";
import { BookOpen, Brain, Camera, Clock3, Heart, Mic, Pause, Play } from "lucide-react";
import type { ChatMessage, MessagePart, Persona } from "@/types";
import { PersonaAvatar } from "./PersonaArt";

const toolIcons: Record<string, typeof Brain> = {
  remember: Brain,
  recall: BookOpen,
  update_relationship: Heart,
  send_photo: Camera,
  send_voice: Mic,
  get_time: Clock3,
  activate_skill: BookOpen,
};

function ToolChip({ part }: { part: Extract<MessagePart, { type: "tool" }> }) {
  const Icon = toolIcons[part.name] ?? Brain;
  return (
    <span className={`tool-chip tool-chip--${part.status}`} title={part.summary || part.title}>
      <Icon size={12} strokeWidth={1.8} />
      <span>{part.title}</span>
      {part.status === "running" && <i className="tool-chip__pulse" />}
    </span>
  );
}

function VoiceBubble({ part }: { part: Extract<MessagePart, { type: "voice" }> }) {
  const audio = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    const element = audio.current;
    if (!element) return;
    const onTime = () => setProgress(element.duration ? element.currentTime / element.duration : 0);
    const onMeta = () => setDuration(Number.isFinite(element.duration) ? element.duration : 0);
    const onEnd = () => { setPlaying(false); setProgress(0); };
    element.addEventListener("timeupdate", onTime);
    element.addEventListener("loadedmetadata", onMeta);
    element.addEventListener("ended", onEnd);
    return () => {
      element.removeEventListener("timeupdate", onTime);
      element.removeEventListener("loadedmetadata", onMeta);
      element.removeEventListener("ended", onEnd);
    };
  }, []);

  const toggle = () => {
    const element = audio.current;
    if (!element) return;
    if (element.paused) {
      void element.play();
      setPlaying(true);
    } else {
      element.pause();
      setPlaying(false);
    }
  };

  const bars = [7, 13, 20, 11, 24, 16, 9, 18, 26, 14, 8, 17, 22, 12, 19, 9, 15, 23, 11, 7];
  return (
    <div className="voice-bubble">
      <audio ref={audio} src={part.url} preload="metadata" />
      <button type="button" className="voice-bubble__play" onClick={toggle} aria-label={playing ? "暂停语音" : "播放语音"}>
        {playing ? <Pause size={15} /> : <Play size={15} fill="currentColor" />}
      </button>
      <div className="voice-bubble__wave" aria-hidden="true">
        {bars.map((height, index) => (
          <i
            key={index}
            style={{ height, opacity: progress > index / bars.length ? 1 : 0.32 }}
          />
        ))}
      </div>
      <span className="voice-bubble__time">{duration ? `${duration.toFixed(0)}″` : "语音"}</span>
    </div>
  );
}

type Props = {
  message: ChatMessage;
  persona: Pick<Persona, "name" | "nameZh" | "palette">;
  previousRole?: string;
  onRetry?: () => void;
  onImage: (url: string) => void;
};

export function MessageBubble({ message, persona, previousRole, onRetry, onImage }: Props) {
  const isUser = message.role === "user";
  // 工具卡只在工具运行中可见；完成后消失，失败交给角色用文字解释，
  // 避免「发一张自拍」这种技术红框破坏沉浸。
  const tools = message.parts.filter((part): part is Extract<MessagePart, { type: "tool" }> =>
    part.type === "tool" && part.status === "running");
  const images = message.parts.filter((part): part is Extract<MessagePart, { type: "image" }> => part.type === "image");
  const voices = message.parts.filter((part): part is Extract<MessagePart, { type: "voice" }> => part.type === "voice");
  const showAvatar = !isUser && previousRole !== "assistant";
  const hasBody = message.content || images.length > 0 || voices.length > 0;

  return (
    <div className={`message-row ${isUser ? "message-row--user" : "message-row--assistant"}`}>
      <div className="message-row__avatar">
        {showAvatar && !isUser ? <PersonaAvatar persona={persona} size={30} /> : null}
      </div>
      <div className={`message-stack ${isUser ? "message-stack--user" : ""}`}>
        {tools.length > 0 && (
          <div className="message-tools">
            {tools.map((part) => <ToolChip key={part.id} part={part} />)}
          </div>
        )}
        {images.length > 0 && (
          <div className="message-images">
            {images.map((part) => (
              <button
                type="button"
                key={part.fileId}
                className="message-image"
                onClick={() => part.url && onImage(part.url)}
                aria-label="查看照片"
              >
                {part.url ? <img src={part.url} alt="照片" loading="lazy" /> : <span className="message-image__loading">照片</span>}
                {part.caption && <span className="message-image__caption">{part.caption}</span>}
              </button>
            ))}
          </div>
        )}
        {voices.length > 0 && (
          <div className="message-voices">
            {voices.map((part) => <VoiceBubble key={part.fileId} part={part} />)}
          </div>
        )}
        {message.content && (
          <div className={`bubble ${isUser ? "bubble--user" : "bubble--assistant"}`}>
            <p>{message.content}{message.streaming && <span className="type-caret" />}</p>
          </div>
        )}
        {message.streaming && !hasBody && (
          <div className="bubble bubble--assistant typing-bubble" aria-label="正在输入">
            <i /><i /><i />
          </div>
        )}
        {message.error && (
          <div className="message-error">
            <span>{message.error}</span>
            {onRetry && <button type="button" onClick={onRetry}>再试一次</button>}
          </div>
        )}
        {isUser && message.pending && <span className="message-sent">发送中…</span>}
      </div>
    </div>
  );
}
