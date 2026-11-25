#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# 默认监听 0.0.0.0，同一 Wi-Fi 下的手机可直接访问；只想本机用 HOST=127.0.0.1 npm run dev。
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-5190}"
export HOST PORT
export VITE_API_TARGET="${VITE_API_TARGET:-http://127.0.0.1:${PORT}}"

if [ ! -d "frontend/node_modules" ]; then
  echo "→ 安装前端依赖"
  npm --prefix frontend install
fi

if [ ! -d "backend/.venv" ]; then
  echo "→ 安装后端依赖"
  uv sync --project backend
fi

cleanup() {
  echo
  echo "→ 正在停止开发服务"
  kill "${API_PID:-}" "${WEB_PID:-}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 取本机局域网 IP，用于打印可被手机打开的地址。
lan_ip() {
  ipconfig getifaddr en0 2>/dev/null \
    || ipconfig getifaddr en1 2>/dev/null \
    || (hostname -I 2>/dev/null | awk '{print $1}')
}

LAN_MODE=0
ACCESS_HOST="$HOST"
if [ "$HOST" = "0.0.0.0" ] || [ "$HOST" = "::" ]; then
  LAN_MODE=1
  ACCESS_HOST="$(lan_ip || true)"
  ACCESS_HOST="${ACCESS_HOST:-你的局域网 IP}"
fi

echo "→ API  http://${ACCESS_HOST}:${PORT}  (演示模式：没有 LLM_API_KEY 时)"
uv run --project backend python -m app &
API_PID=$!

if [ "$LAN_MODE" = "1" ]; then
  export VITE_HOST="$HOST"
  # IP 访问默认放行；额外放行 xxx.local 这类 mDNS 主机名。
  export VITE_ALLOWED_HOSTS="${VITE_ALLOWED_HOSTS:-.local}"
  echo "→ Web  http://${ACCESS_HOST}:5191"
  echo "   局域网模式：同一 Wi-Fi 下的设备可直接打开上面的 Web 地址。"
  echo "   首次监听 0.0.0.0 时 macOS 可能弹窗，请允许 node / python 接受传入连接。"
else
  echo "→ Web  http://${ACCESS_HOST}:5191"
  echo "   仅本机可访问（HOST=127.0.0.1）。"
fi

npm --prefix frontend run dev &
WEB_PID=$!

wait
