# 本地后端 + Cloudflare Tunnel 方案

因 Cloudflare Containers beta 未对该账号开放（`No such module "cloudflare:containers"`），当前采用「后端跑本机 + Tunnel 暴露固定子域名」方案，速度最快、调试最方便。

## 架构
- **前端**：`https://loveshop.us.ci`（Cloudflare Pages）
- **后端**：你 MacBook 本地 FastAPI（`http://localhost:8000`）
- **桥接**：`cloudflared tunnel` 把 `https://api.loveshop.us.ci` 映射到本机 8000 端口

## 一键启动

```bash
cd /Users/like/WorkBuddy/2026-08-21-10-49-01/ai-media-pipeline
./run-local-api.sh
```

脚本会：安装/检查依赖、启动后端、健康检查，然后告诉你下一步启动 tunnel。

## 首次配置 Cloudflare Tunnel

```bash
brew install cloudflared
cloudflared tunnel login          # 浏览器授权，选你的 Cloudflare 账号
cloudflared tunnel create ai-media-api
cloudflared tunnel route dns <UUID> api.loveshop.us.ci
cloudflared tunnel run --url http://localhost:8000 <UUID>
```

`<UUID>` 创建隧道时输出的一串 id。

或使用配置文件（推荐，便于常驻）：

```bash
cat > ~/.cloudflared/config.yml <<EOF
tunnel: <UUID>
credentials-file: /Users/like/.cloudflared/<UUID>.json
ingress:
  - hostname: api.loveshop.us.ci
    service: http://localhost:8000
  - service: http_status:404
EOF
cloudflared tunnel run ai-media-api
```

## 验证

```bash
curl https://api.loveshop.us.ci/api/health
```

返回 `{"status":"ok",...}` 即通。

然后打开 `https://loveshop.us.ci` →「⑦ 一键生成视频」→ 填话题 → 出文案。

## 局限
- 你的 MacBook 必须开机且后端在跑，网页才能生成。
- 若不想本机常驻，可申请 Cloudflare Containers beta，或换 Railway/Render/Fly。
- 当前 `RENDER_VIDEO=0`，所以出的是脚本/素材文案，不是视频；要出视频需在本地装好 Remotion 并设 `RENDER_VIDEO=1`。
