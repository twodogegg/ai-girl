import type { Persona } from "@/types";
import { PersonaArt } from "./PersonaArt";

export function PersonaCard({ persona, onOpen }: { persona: Persona; onOpen: (persona: Persona) => void }) {
  return (
    <button type="button" className="persona-card" onClick={() => onOpen(persona)}>
      <PersonaArt persona={persona} variant="card" />
      <div className="persona-card__shade" />
      <div className="persona-card__top">
        {persona.online && <span className="online-dot" title="在线" />}
        <span className="persona-card__age">{persona.age}</span>
      </div>
      <div className="persona-card__body">
        <h3 className="persona-card__name">{persona.nameZh || persona.name}</h3>
        <p className="persona-card__meta">{persona.occupation}</p>
        <div className="persona-card__tags">
          {persona.tags.slice(0, 2).map((tag) => <span key={tag} className="tag tag--ghost">{tag}</span>)}
        </div>
      </div>
    </button>
  );
}

export function FeaturedCard({ persona, onOpen }: { persona: Persona; onOpen: (persona: Persona) => void }) {
  return (
    <button type="button" className="featured-card" onClick={() => onOpen(persona)}>
      <PersonaArt persona={persona} variant="hero" />
      <div className="featured-card__shade" />
      <div className="featured-card__content">
        <span className="eyebrow">TONIGHT&apos;S PICK</span>
        <h3>{persona.nameZh || persona.name}</h3>
        <p>{persona.tagline}</p>
        <span className="featured-card__cta">认识她 <span aria-hidden="true">→</span></span>
      </div>
    </button>
  );
}

