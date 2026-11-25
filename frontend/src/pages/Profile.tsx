import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronRight, LogOut, Moon, ShieldCheck, Sun, UserRound } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useApp } from "@/context/AppContext";

export function Profile() {
  const { user, logout, ageConfirmed } = useAuth();
  const { theme, toggleTheme, toast } = useApp();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);

  const signOut = async () => {
    setBusy(true);
    try {
      await logout();
      toast("已经离开夜色。");
      navigate("/");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page profile">
      <header className="page-head">
        <span className="eyebrow">YOUR SPACE</span>
        <h1>我的</h1>
        <p>这里放着你留下的痕迹。</p>
      </header>

      <section className="profile-card">
        <div className="profile-card__avatar">
          {user ? user.displayName.slice(0, 1) : <UserRound size={24} />}
        </div>
        <div className="profile-card__body">
          <h2>{user ? user.displayName : "还没有登录"}</h2>
          <p>{user ? `@${user.username}` : "登录后，她会记得你。"}</p>
        </div>
        {user ? (
          <span className="badge">{user.role === "admin" ? "主理人" : user.username.startsWith("guest_") ? "访客" : "会员"}</span>
        ) : (
          <Link className="soft-button" to="/login?next=/me">登录</Link>
        )}
      </section>

      <section className="settings-card">
        <div className="settings-row">
          <span className="settings-row__icon"><ShieldCheck size={18} /></span>
          <div className="settings-row__body">
            <strong>成年确认</strong>
            <p>{ageConfirmed || user?.adultConfirmed ? "已确认你年满 18 周岁" : "尚未确认"}</p>
          </div>
          <span className={`status-dot${ageConfirmed || user?.adultConfirmed ? " is-on" : ""}`} />
        </div>
        <button type="button" className="settings-row" onClick={toggleTheme}>
          <span className="settings-row__icon">{theme === "dark" ? <Moon size={18} /> : <Sun size={18} />}</span>
          <div className="settings-row__body">
            <strong>外观</strong>
            <p>{theme === "dark" ? "Night Craft · 暖黑与琥珀" : "Japanese Minimal · 和纸与陶土"}</p>
          </div>
          <ChevronRight size={17} className="settings-row__chevron" />
        </button>
      </section>

      {user?.role === "admin" && (
        <section className="settings-card">
          <Link className="settings-row" to="/admin">
            <span className="settings-row__icon"><UserRound size={18} /></span>
            <div className="settings-row__body">
              <strong>主理人后台</strong>
              <p>编辑人设、工具与 Skills</p>
            </div>
            <ChevronRight size={17} className="settings-row__chevron" />
          </Link>
        </section>
      )}

      <section className="settings-card settings-card--about">
        <h3>关于这里</h3>
        <p>
          PLOT18 是一个成年人限定的 AI 陪伴体验。所有角色均为虚构成年人，
          对话由模型生成，不会联系现实中的任何人。
        </p>
        <p>
          你可以随时清空对话、删除记忆或退出。遇到现实中的困扰，请优先联系可信任的人或当地专业机构。
        </p>
        <p className="muted">PLOT18 · build 0.1 · Night Craft</p>
      </section>

      {user && (
        <button type="button" className="button button--soft button--full profile-logout" disabled={busy} onClick={() => void signOut()}>
          <LogOut size={16} /> {busy ? "正在退出…" : "退出登录"}
        </button>
      )}

      <footer className="page-foot">
        <span>虚构角色 · 成年人限定</span>
        <span>请照顾好自己</span>
      </footer>
    </div>
  );
}
