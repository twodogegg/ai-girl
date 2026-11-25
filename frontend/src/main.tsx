import React from "react";
import ReactDOM from "react-dom/client";
import "@fontsource-variable/geist";
import "@/styles/tokens.css";
import "@/styles/base.css";
import "@/styles/discover.css";
import "@/styles/chat.css";
import "@/styles/pages.css";
import "@/styles/admin.css";
import { App } from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
