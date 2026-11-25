import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";

type Props = {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  className?: string;
};

export function Sheet({ open, onClose, title, children, className = "" }: Props) {
  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="sheet-layer" role="dialog" aria-modal="true" aria-label={title}>
      <button type="button" className="sheet-backdrop" aria-label="关闭" onClick={onClose} />
      <div className={`sheet ${className}`}>
        <div className="sheet__grab" aria-hidden="true" />
        <div className="sheet__head">
          <span className="sheet__title">{title}</span>
          <button type="button" className="icon-button" onClick={onClose} aria-label="关闭">
            <X size={18} />
          </button>
        </div>
        <div className="sheet__body">{children}</div>
      </div>
    </div>
  );
}
