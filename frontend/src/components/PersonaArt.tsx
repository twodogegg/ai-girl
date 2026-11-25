import type { CSSProperties } from "react";
import type { Persona } from "@/types";

type Props = {
  persona: Pick<Persona, "name" | "nameZh" | "palette">;
  variant?: "card" | "hero" | "avatar" | "thumb";
  className?: string;
};

export function PersonaArt({ persona, variant = "card", className = "" }: Props) {
  const [a, b] = persona.palette;
  const style = { "--art-a": a, "--art-b": b } as CSSProperties;
  const initial = (persona.nameZh || persona.name || "?").slice(0, 1);
  return (
    <div className={`persona-art persona-art--${variant} ${className}`} style={style} aria-hidden="true">
      <div className="persona-art__glow" />
      <svg className="persona-art__lines" viewBox="0 0 300 400" fill="none" preserveAspectRatio="xMidYMax slice">
        <path d="M214 96c18 32 16 74-4 102-8 12-20 22-24 34-3 9 2 20 10 25" stroke="currentColor" strokeWidth="0.7" opacity=".42" />
        <path d="M105 110c-19 28-23 66-10 96 7 17 22 26 26 42 3 12-2 25-8 34" stroke="currentColor" strokeWidth="0.7" opacity=".3" />
        <path d="M150 88c-24 0-43 20-43 46s19 47 43 47 43-21 43-47-19-46-43-46Z" stroke="currentColor" strokeWidth="0.8" opacity=".55" />
        <path d="M118 151c8-5 17-5 24-1M158 150c8-5 17-5 24 1" stroke="currentColor" strokeWidth="0.9" opacity=".5" />
        <path d="M150 158c-2 10-3 17 2 21 3 3 8 3 12 1" stroke="currentColor" strokeWidth="0.7" opacity=".4" />
        <path d="M138 198c8 5 17 5 24 0" stroke="currentColor" strokeWidth="0.8" opacity=".45" />
        <path d="M150 234v26" stroke="currentColor" strokeWidth="0.8" opacity=".35" />
        <path d="M64 400c8-62 38-101 86-118 48 17 78 56 86 118" stroke="currentColor" strokeWidth="0.8" opacity=".45" />
        <path d="M94 400c5-44 25-71 56-85 31 14 51 41 56 85" stroke="currentColor" strokeWidth="0.6" opacity=".25" />
        <circle cx="228" cy="72" r="20" stroke="currentColor" strokeWidth="0.6" opacity=".28" />
        <circle cx="228" cy="72" r="27" stroke="currentColor" strokeWidth="0.4" opacity=".12" />
      </svg>
      <span className="persona-art__initial">{initial}</span>
      <div className="persona-art__grain" />
      <div className="persona-art__vignette" />
    </div>
  );
}

export function PersonaAvatar({ persona, size = 40 }: { persona: Pick<Persona, "name" | "nameZh" | "palette">; size?: number }) {
  return (
    <div style={{ width: size, height: size }}>
      <PersonaArt persona={persona} variant="avatar" className="persona-avatar" />
    </div>
  );
}
