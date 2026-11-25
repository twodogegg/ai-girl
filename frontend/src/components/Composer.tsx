import { useEffect, useRef, useState } from "react";
import { ArrowUp, Camera, Square, X } from "lucide-react";

type Props = {
  sending: boolean;
  uploading: boolean;
  onSend: (text: string, files: File[]) => void | Promise<void>;
  onStop: () => void;
  placeholder?: string;
};

type Picked = { file: File; url: string };

export function Composer({ sending, uploading, onSend, onStop, placeholder = "说点什么…" }: Props) {
  const [text, setText] = useState("");
  const [picked, setPicked] = useState<Picked[]>([]);
  const input = useRef<HTMLInputElement | null>(null);
  const area = useRef<HTMLTextAreaElement | null>(null);
  const busy = sending || uploading;

  useEffect(() => {
    const element = area.current;
    if (!element) return;
    element.style.height = "0px";
    element.style.height = `${Math.min(element.scrollHeight, 116)}px`;
  }, [text]);

  const submit = async () => {
    if (busy) return;
    const value = text.trim();
    if (!value && picked.length === 0) return;
    const files = picked.map((item) => item.file);
    setText("");
    picked.forEach((item) => URL.revokeObjectURL(item.url));
    setPicked([]);
    if (area.current) area.current.style.height = "0px";
    await onSend(value, files);
  };

  const addFiles = (files: FileList | null) => {
    if (!files) return;
    const next: Picked[] = [];
    for (const file of Array.from(files).slice(0, 4 - picked.length)) {
      if (!file.type.startsWith("image/")) continue;
      next.push({ file, url: URL.createObjectURL(file) });
    }
    if (next.length) setPicked((current) => [...current, ...next].slice(0, 4));
    if (input.current) input.current.value = "";
  };

  return (
    <div className="composer">
      {picked.length > 0 && (
        <div className="composer__previews">
          {picked.map((item) => (
            <div key={item.url} className="composer__preview">
              <img src={item.url} alt="待发送照片" />
              <button
                type="button"
                aria-label="移除照片"
                onClick={() => {
                  URL.revokeObjectURL(item.url);
                  setPicked((current) => current.filter((entry) => entry.url !== item.url));
                }}
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
      {uploading && <div className="composer__hint">正在上传照片…</div>}
      <div className="composer__bar">
        <input
          ref={input}
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={(event) => addFiles(event.target.files)}
        />
        <button
          type="button"
          className="composer__photo"
          aria-label="发送照片"
          disabled={busy || picked.length >= 4}
          onClick={() => input.current?.click()}
        >
          <Camera size={20} strokeWidth={1.7} />
        </button>
        <textarea
          ref={area}
          className="composer__input"
          value={text}
          rows={1}
          maxLength={4000}
          placeholder={placeholder}
          onChange={(event) => setText(event.target.value)}
          onFocus={() => window.setTimeout(() => area.current?.scrollIntoView({ block: "nearest" }), 240)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              void submit();
            }
          }}
        />
        {sending ? (
          <button type="button" className="composer__stop" aria-label="停止回复" onClick={onStop}>
            <Square size={15} fill="currentColor" />
          </button>
        ) : (
          <button
            type="button"
            className={`composer__send${text.trim() || picked.length ? " is-ready" : ""}`}
            aria-label="发送"
            disabled={(!text.trim() && picked.length === 0) || uploading}
            onClick={() => void submit()}
          >
            <ArrowUp size={20} strokeWidth={2.2} />
          </button>
        )}
      </div>
      <p className="composer__fine">虚构角色 · 成年人之间的自愿对话 · 随时可以停下</p>
    </div>
  );
}
