#!/bin/zsh
# OpenMarvis 一键启动脚本
# 用法：双击运行，或在终端执行 ./start.sh

set -e
PROJECT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$PROJECT/apps/backend"
WEB="$PROJECT/apps/web"
LOG_DIR="$PROJECT/.logs"
mkdir -p "$LOG_DIR"

# ── 颜色 ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo "${GREEN}[OpenMarvis]${NC} $1"; }
warn()  { echo "${YELLOW}[OpenMarvis]${NC} $1"; }
error() { echo "${RED}[OpenMarvis]${NC} $1"; exit 1; }

# ── 检查端口是否已被占用 ──────────────────────────────────────────────
port_in_use() { lsof -i ":$1" -sTCP:LISTEN -t &>/dev/null; }

# ── 关闭所有子进程（Ctrl+C 时触发）──────────────────────────────────
cleanup() {
  echo ""
  warn "正在关闭服务..."
  kill $BACKEND_PID $WEB_PID 2>/dev/null || true
  wait $BACKEND_PID $WEB_PID 2>/dev/null || true
  warn "已退出。下次直接运行 ./start.sh 重新启动。"
}
trap cleanup INT TERM

# ── 检查依赖 ─────────────────────────────────────────────────────────
[[ -f "$BACKEND/.venv/bin/uvicorn" ]] || \
  error "后端未安装，请先运行：cd $PROJECT && make install"

[[ -f "$WEB/node_modules/.bin/next" ]] || \
  error "前端未安装，请先运行：cd $PROJECT && make install"

[[ -f "$BACKEND/.env" ]] || \
  error ".env 不存在，请先复制：cp $BACKEND/.env.example $BACKEND/.env 并填入 API Key"

# ── 启动后端 ─────────────────────────────────────────────────────────
if port_in_use 8000; then
  warn "端口 8000 已有服务在运行，跳过启动后端"
else
  info "启动后端（FastAPI :8000）..."
  cd "$BACKEND"
  .venv/bin/uvicorn openmarvis.main:app --port 8000 \
    > "$LOG_DIR/backend.log" 2>&1 &
  BACKEND_PID=$!
  # 等待后端就绪
  for i in $(seq 1 20); do
    sleep 0.5
    curl -s http://127.0.0.1:8000/healthz &>/dev/null && break
    [[ $i -eq 20 ]] && error "后端启动超时，查看日志：$LOG_DIR/backend.log"
  done
  info "后端已就绪 ✓"
fi

# ── 启动前端 ─────────────────────────────────────────────────────────
if port_in_use 3000; then
  warn "端口 3000 已有服务在运行，跳过启动前端"
else
  info "启动前端（Next.js :3000）..."
  cd "$WEB"
  npm run dev > "$LOG_DIR/web.log" 2>&1 &
  WEB_PID=$!
  # 等待前端就绪
  for i in $(seq 1 30); do
    sleep 1
    curl -s http://localhost:3000 &>/dev/null && break
    [[ $i -eq 30 ]] && error "前端启动超时，查看日志：$LOG_DIR/web.log"
  done
  info "前端已就绪 ✓"
fi

# ── 打开浏览器 ────────────────────────────────────────────────────────
info "打开浏览器 → http://localhost:3000"
open http://localhost:3000

echo ""
info "OpenMarvis 运行中。按 Ctrl+C 关闭所有服务。"
echo "  后端日志：$LOG_DIR/backend.log"
echo "  前端日志：$LOG_DIR/web.log"
echo ""

# 保持脚本存活，等待子进程
wait $BACKEND_PID $WEB_PID 2>/dev/null || true
