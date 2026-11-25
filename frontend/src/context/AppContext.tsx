import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

type Theme = "dark" | "light";
type ToastItem = { id: number; text: string };

type AppContextValue = {
  theme: Theme;
  toggleTheme: () => void;
  toast: (text: string) => void;
};

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem("plot18:theme") === "light" ? "light" : "dark"));
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    const meta = document.querySelector('meta[name="theme-color"]');
    meta?.setAttribute("content", theme === "dark" ? "#101114" : "#F7F1E8");
    localStorage.setItem("plot18:theme", theme);
  }, [theme]);

  const toast = (text: string) => {
    const id = Date.now() + Math.random();
    setToasts((items) => [...items, { id, text }]);
    window.setTimeout(() => setToasts((items) => items.filter((item) => item.id !== id)), 2600);
  };

  const value = useMemo<AppContextValue>(() => ({
    theme,
    toggleTheme: () => setTheme((current) => (current === "dark" ? "light" : "dark")),
    toast,
  }), [theme]);

  return (
    <AppContext.Provider value={value}>
      {children}
      <div className="toast-stack" aria-live="polite">
        {toasts.map((item) => <div key={item.id} className="toast">{item.text}</div>)}
      </div>
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used inside AppProvider");
  return context;
}
