import { NavLink } from "react-router-dom";
import { Compass, MessageCircle, UserRound } from "lucide-react";

const items = [
  { to: "/", label: "发现", icon: Compass, end: true },
  { to: "/chats", label: "消息", icon: MessageCircle, end: false },
  { to: "/me", label: "我的", icon: UserRound, end: false },
];

export function BottomNav() {
  return (
    <nav className="bottom-nav" aria-label="主导航">
      {items.map(({ to, label, icon: Icon, end }) => (
        <NavLink key={to} to={to} end={end} className={({ isActive }) => `bottom-nav__item${isActive ? " is-active" : ""}`}>
          <Icon size={21} strokeWidth={1.7} />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
