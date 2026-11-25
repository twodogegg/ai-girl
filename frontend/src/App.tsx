import { useEffect } from "react";
import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { AppProvider } from "@/context/AppContext";
import { AgeGate } from "@/components/AgeGate";
import { BottomNav } from "@/components/BottomNav";
import { Discover } from "@/pages/Discover";
import { Chats } from "@/pages/Chats";
import { ChatPage } from "@/pages/ChatPage";
import { Profile } from "@/pages/Profile";
import { Login } from "@/pages/Login";
import { Admin } from "@/pages/Admin";

function Shell() {
  const location = useLocation();
  useEffect(() => {
    document.querySelector(".app-main")?.scrollTo({ top: 0 });
  }, [location.pathname]);
  return (
    <div className="app-shell">
      <main className="app-main"><Outlet /></main>
      <BottomNav />
    </div>
  );
}

function ScrollToTop() {
  const location = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [location.pathname]);
  return null;
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppProvider>
          <AgeGate />
          <ScrollToTop />
          <Routes>
            <Route element={<Shell />}>
              <Route path="/" element={<Discover />} />
              <Route path="/chats" element={<Chats />} />
              <Route path="/me" element={<Profile />} />
            </Route>
            <Route path="/chat/:personaId" element={<ChatPage />} />
            <Route path="/login" element={<Login />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AppProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
