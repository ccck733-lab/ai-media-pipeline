#!/usr/bin/env bash
# 本地一键启动后端 +  Cloudflare Tunnel 暴露 api.loveshop.us.ci
# 依赖：Python 3.x / wrangler 安装的 venv / cloudflared
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/.workbuddy/binaries/python/envs/default"

# 1. 确保后端依赖
if [ ! -x "$VENV/bin/python" ]; then
  /Users/like/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q --disable-pip-version-check -r "$REPO/api/requirements.txt"

# 2. 启动后端（监听 0.0.0.0:8000）
echo "→ 启动 FastAPI 后端 http://localhost:8000"
"$VENV/bin/python" "$REPO/api/server.py" &
SRV=$!
sleep 2

# 3. 健康检查
curl -s http://localhost:8000/api/health >/dev/null && echo "→ 后端健康检查通过" || { echo "后端启动失败"; kill $SRV 2>/dev/null; exit 1; }

# 4. 提示启动 tunnel（由你手动执行一次，之后可写进 launchd 常驻）
echo ""
echo "=== 后端已就绪。请在另一个终端启动 Cloudflare Tunnel： ==="
echo "cloudflared tunnel run ai-media-api"
echo ""
echo "若尚未创建 tunnel，先执行："
echo "  brew install cloudflared"
echo "  cloudflared tunnel login"
echo "  cloudflared tunnel create ai-media-api"
echo "  cloudflared tunnel route dns \$(cloudflared tunnel list | grep ai-media-api | awk '{print \$1}') api.loveshop.us.ci"
echo ""
echo "保持本窗口运行。按 Ctrl+C 停止后端。"
wait $SRV
