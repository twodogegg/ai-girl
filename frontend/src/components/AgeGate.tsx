import { useState } from "react";
import { useAuth } from "@/context/AuthContext";

export function AgeGate() {
  const { ageConfirmed, confirmAge } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (ageConfirmed) return null;

  const confirm = async () => {
    setBusy(true);
    setError("");
    try {
      await confirmAge();
    } catch (err) {
      setError(err instanceof Error ? err.message : "确认失败，请重试。");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="age-gate">
      <div className="age-gate__panel">
        <span className="eyebrow">BEFORE WE BEGIN</span>
        <h1>今夜之前，<br />先确认一件事。</h1>
        <p>
          这里是一段为成年人准备的虚构关系体验。所有角色均为 18 岁以上的虚构成年人，
          对话与画面不涉及现实中的任何人。
        </p>
        <p className="age-gate__fine">
          进入即表示你已年满 18 周岁，并理解这是 AI 角色扮演，而非真实关系。
          你可以随时停下，也可以随时离开。
        </p>
        {error && <p className="form-error">{error}</p>}
        <button type="button" className="button button--primary button--full" disabled={busy} onClick={() => void confirm()}>
          {busy ? "正在确认…" : "我已满 18 岁"}
        </button>
        <a className="age-gate__leave" href="https://www.google.com">我还没准备好</a>
      </div>
    </div>
  );
}
