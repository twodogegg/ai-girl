import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Search, Sparkles } from "lucide-react";
import type { Persona } from "@/types";
import { useAuth } from "@/context/AuthContext";
import { usePersonas } from "@/hooks/usePersonas";
import { FeaturedCard, PersonaCard } from "@/components/PersonaCard";
import { PersonaSheet } from "@/components/PersonaSheet";

const TAGS = ["全部", "校园", "轻熟", "Idol", "制服", "亚文化", "邻家", "声音", "日系", "职场"];

export function Discover() {
  const { personas, loading, error, query, setQuery, tag, setTag } = usePersonas();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<Persona | null>(null);

  const featured = useMemo(() => {
    const wanted = ["chloe-miller", "ji-eun-park", "su-mo"];
    const picked = wanted.map((id) => personas.find((item) => item.id === id)).filter(Boolean) as Persona[];
    return picked.length ? picked : personas.slice(0, 3);
  }, [personas]);

  const start = (persona: Persona) => {
    setSelected(null);
    if (!user) {
      navigate(`/login?next=${encodeURIComponent(`/chat/${persona.id}`)}`);
      return;
    }
    navigate(`/chat/${persona.id}`);
  };

  return (
    <div className="page discover">
      <header className="topbar">
        <Link to="/" className="wordmark">plot<span>.</span>18</Link>
        <div className="topbar__right">
          <span className="topbar__live"><i /> {personas.length || "—"} 位今晚在线</span>
          {user ? (
            <Link to="/me" className="topbar__avatar">{user.displayName.slice(0, 1)}</Link>
          ) : (
            <Link to="/login" className="soft-link">登录</Link>
          )}
        </div>
      </header>

      <section className="hero">
        <span className="eyebrow">AFTER HOURS · 只属于今晚</span>
        <h1>今晚，<br />想和谁说话？</h1>
        <p className="hero__sub">
          选一个她，从一句“在吗”开始。她会记得你说过的事，也会在某个夜里先想起你。
        </p>
        <label className="search">
          <Search size={17} strokeWidth={1.8} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="找一个名字、职业或气质…"
            aria-label="搜索人设"
          />
        </label>
        <div className="hero__note">
          <Sparkles size={13} />
          所有角色均为 18 岁以上的虚构成年人
        </div>
      </section>

      <div className="filter-rail" role="tablist" aria-label="筛选">
        {TAGS.map((item) => {
          const value = item === "全部" ? "" : item;
          const active = tag === value;
          return (
            <button
              key={item}
              type="button"
              role="tab"
              aria-selected={active}
              className={`filter-chip${active ? " is-active" : ""}`}
              onClick={() => setTag(value)}
            >
              {item}
            </button>
          );
        })}
      </div>

      {!loading && featured.length > 0 && (
        <section className="section">
          <div className="section__head">
            <span className="eyebrow">TONIGHT&apos;S PICK</span>
            <h2>今晚精选</h2>
            <p>如果你还没想好，从她们开始。</p>
          </div>
          <div className="featured-rail">
            {featured.map((persona) => (
              <FeaturedCard key={persona.id} persona={persona} onOpen={setSelected} />
            ))}
          </div>
        </section>
      )}

      <section className="section">
        <div className="section__head section__head--row">
          <div>
            <span className="eyebrow">ALL CHARACTERS</span>
            <h2>{tag ? `${tag}的她` : "所有人"}</h2>
          </div>
          <span className="section__count">{personas.length} 位</span>
        </div>

        {error && <p className="form-error">{error}</p>}
        {loading ? (
          <div className="persona-grid">
            {Array.from({ length: 6 }).map((_, index) => <div key={index} className="persona-card persona-card--skeleton" />)}
          </div>
        ) : personas.length === 0 ? (
          <div className="empty-state">
            <h3>没有找到她</h3>
            <p>换一个词，或者看看全部人设。</p>
            <button type="button" className="soft-button" onClick={() => { setQuery(""); setTag(""); }}>看看所有人</button>
          </div>
        ) : (
          <div className="persona-grid">
            {personas.map((persona) => <PersonaCard key={persona.id} persona={persona} onOpen={setSelected} />)}
          </div>
        )}
      </section>

      <footer className="page-foot">
        <span>PLOT18 · 深夜关系现场</span>
        <span>虚构角色 · 成年人限定 · 请照顾好自己</span>
      </footer>

      <PersonaSheet persona={selected} onClose={() => setSelected(null)} onStart={start} />
    </div>
  );
}
