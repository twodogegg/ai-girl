import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// VITE_HOST=0.0.0.0 时允许局域网设备访问；VITE_ALLOWED_HOSTS 用于放行 mDNS 等主机名。
const host = process.env.VITE_HOST || "127.0.0.1";
const apiTarget = process.env.VITE_API_TARGET || "http://127.0.0.1:5190";
const allowedHosts = (process.env.VITE_ALLOWED_HOSTS || "")
  .split(",")
  .map((item) => item.trim())
  .filter(Boolean);

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host,
    allowedHosts: allowedHosts.length ? allowedHosts : undefined,
    port: 5191,
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: false,
      },
    },
  },
  preview: {
    host,
    allowedHosts: allowedHosts.length ? allowedHosts : undefined,
    port: 5191,
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
