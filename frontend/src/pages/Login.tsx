import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, Ghost } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export function Login() {
  const { user, login, register, guest } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const nextParam = params.get("next") || "/";
  const next = nextParam.startsWith("/") && !nextParam.startsWith("//") ? nextParam : "/";

  useEffect(() => {
    if (user) navigate(next, { replace: true });
  }, [navigate, next, user]);

  if (user) return null;

  const submit = async () => {
    if (busy) return;
    setError("");
    setBusy("form");
    try {
      if (mode === "login") await login(username.trim(), password);
      else await register(username.trim(), password, displayName.trim());
      navigate(next, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败，请重试。");
    } finally {
      setBusy("");
    }
  };

  const enterAsGuest = async () => {
    if (busy) return;
    setError("");
    setBusy("guest");
    try {
      await guest();
      navigate(next, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "访客登录失败。");
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="auth-page">
      <header className="auth-top">
        <Link to="/" className="icon-button" aria-label="返回">
          <ArrowLeft size={20} />
        </Link>
        <Link to="/" className="wordmark">plot<span>.</span>18</Link>
        <span className="auth-top__badge">18+</span>
      </header>

      <div className="auth-card">
        <span className="eyebrow">YOUR PRIVATE LINE</span>
        <h1>{mode === "login" ? "欢迎回来。" : "留一个名字。"}</h1>
        <p className="auth-sub">
          {mode === "login"
            ? "她会记得上次聊到哪里。"
            : "不需要邮箱，取一个只有这里知道的名字。"}
        </p>

        <div className="auth-tabs">
          <button type="button" className={mode === "login" ? "is-active" : ""} onClick={() => setMode("login")}>登录</button>
          <button type="button" className={mode === "register" ? "is-active" : ""} onClick={() => setMode("register")}>注册</button>
        </div>

        <form
          className="auth-form"
          onSubmit={(event) => { event.preventDefault(); void submit(); }}
        >
          <label className="field">
            <span>用户名</span>
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              placeholder="字母、数字或下划线"
              required
            />
          </label>
          {mode === "register" && (
            <label className="field">
              <span>她怎么叫你</span>
              <input
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                placeholder="昵称，可以随时不填"
                maxLength={24}
              />
            </label>
          )}
          <label className="field">
            <span>密码</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              placeholder="至少 6 位"
              required
            />
          </label>
          {error && <p className="form-error">{error}</p>}
          <button type="submit" className="button button--primary button--full" disabled={Boolean(busy)}>
            {busy === "form" ? "正在进入…" : mode === "login" ? "进入夜色" : "创建账号"}
          </button>
        </form>

        <div className="auth-divider"><span>或者</span></div>

        <button type="button" className="button button--soft button--full" disabled={Boolean(busy)} onClick={() => void enterAsGuest()}>
          <Ghost size={17} />
          {busy === "guest" ? "正在准备…" : "以访客身份进入"}
        </button>
        <p className="auth-fine">
          继续即表示你已年满 18 周岁。这里的所有角色均为虚构成年人，
          对话由 AI 生成，不代表真实的人或关系。
        </p>
      </div>
    </div>
  );
}
