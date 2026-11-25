import { ArrowRight, MapPin, MessageCircle } from "lucide-react";
import type { Persona } from "@/types";
import { PersonaArt } from "./PersonaArt";
import { Sheet } from "./Sheet";

type Props = {
  persona: Persona | null;
  onClose: () => void;
  onStart: (persona: Persona) => void;
};

const stageLabel: Record<string, string> = {
  stranger: "刚刚认识",
  acquaintance: "开始熟悉",
  close: "有点暧昧",
  lover: "亲密",
};

export function PersonaSheet({ persona, onClose, onStart }: Props) {
  return (
    <Sheet open={Boolean(persona)} onClose={onClose} title="她" className="persona-sheet">
      {persona && (
        <>
          <div className="persona-sheet__hero">
            <PersonaArt persona={persona} variant="hero" />
            <div className="persona-sheet__hero-shade" />
            <div className="persona-sheet__hero-text">
              <span className="eyebrow">MEET {persona.name.toUpperCase()}</span>
              <h1>{persona.nameZh || persona.name}<span className="persona-sheet__age">{persona.age}</span></h1>
              <p>{persona.tagline}</p>
            </div>
          </div>

          <div className="persona-sheet__facts">
            <span><MapPin size={13} /> {persona.city}</span>
            <span>{persona.occupation}</span>
            <span>{persona.languages.join(" · ")}</span>
          </div>

          <div className="persona-sheet__tags">
            {persona.tags.map((tag) => <span key={tag} className="tag">{tag}</span>)}
          </div>

          <section className="persona-sheet__section">
            <h2>关于她</h2>
            <p>{persona.bio}</p>
            <p className="muted">{persona.personality}</p>
          </section>

          <section className="persona-sheet__section">
            <h2>她说话的方式</h2>
            <p>{persona.speakingStyle}</p>
          </section>

          <section className="persona-sheet__section">
            <h2>你们之间</h2>
            <p>{persona.relationship}</p>
            {persona.relationshipState && (
              <div className="relationship-strip">
                <span>认识第 {persona.relationshipState.daysKnown} 天</span>
                <span>{stageLabel[persona.relationshipState.stage] || persona.relationshipState.stage}</span>
                <span className="relationship-strip__meter">
                  <i style={{ width: `${persona.relationshipState.affinity}%` }} />
                </span>
              </div>
            )}
          </section>

          <section className="persona-sheet__section">
            <h2>从这句话开始</h2>
            <div className="starter-list">
              {persona.starters.map((starter) => (
                <span key={starter} className="starter-chip">{starter}</span>
              ))}
            </div>
          </section>

          <div className="persona-sheet__cta">
            <button type="button" className="button button--primary button--full" onClick={() => onStart(persona)}>
              <MessageCircle size={17} />
              {persona.conversationId ? "继续今晚的话题" : "开始聊天"}
              <ArrowRight size={16} />
            </button>
            <p>她记得你们说过的话。所有角色均为虚构成年人。</p>
          </div>
        </>
      )}
    </Sheet>
  );
}
