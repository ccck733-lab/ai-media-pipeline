#!/usr/bin/env bash
# 本地一键启动 AI 自媒体流水线后端
# 启动后访问 http://localhost:8000 即可使用内嵌控制台一键生成
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/.workbuddy/binaries/python/envs/default"
PIDFILE="$REPO/.api.pid"

# 1. 确保后端依赖
if [ ! -x "$VENV/bin/python" ]; then
  /Users/like/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q --disable-pip-version-check -r "$REPO/api/requirements.txt"

# 2. 如果已有后端在跑，先停掉（避免端口冲突）
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "→ 停止旧后端进程 $(cat "$PIDFILE")"
  kill "$(cat "$PIDFILE")" 2>/dev/null || true
  sleep 1
fi

# 3. 启动后端（监听 0.0.0.0:8000），后台运行
nohup "$VENV/bin/python" "$REPO/api/server.py" > "$REPO/api.log" 2>&1 &
SRV=$!
echo $SRV > "$PIDFILE"
echo "→ 启动 FastAPI 后端 http://localhost:8000 (PID $SRV)"
sleep 2

# 4. 健康检查
if curl -s http://localhost:8000/api/health >/dev/null; then
  echo "→ 后端健康检查通过"
else
  echo "✗ 后端启动失败，请查看 $REPO/api.log"
  kill $SRV 2>/dev/null || true
  rm -f "$PIDFILE"
  exit 1
fi

echo ""
echo "=== 后端已就绪 ==="
echo "浏览器打开：http://localhost:8000"
echo "控制台内「⑦ 一键生成视频」即可调用本地流水线。"
echo ""
echo "如需停止：kill $(cat "$PIDFILE")  或  ./stop-local-api.sh"
echo "如需远程访问（本机当前网络受限，可换网络再试）："
echo "  ngrok http 127.0.0.1:8000"
echo "  cloudflared tunnel --url http://127.0.0.1:8000"
