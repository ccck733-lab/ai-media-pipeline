# 部署 AI 自媒体控制台到 Cloudflare

## ★ 当前生效方案：cloudflared 隧道 → 根域名 loveshop.us.ci（2026-08-22 验证通过）

控制台要"在线一键生成视频"必须连后端（FastAPI + Python + Remotion + ffmpeg，跑在本地 Mac）。
Cloudflare Pages 跑不了这个后端，所以**用 cloudflared 隧道把根域名指到本地后端**，整站（界面+API）都在线。

> 前提：wrangler 的 OAuth 已登录（`wrangler whoami` 可见 ccck733@gmail.com）；`~/.cloudflared/` 有 cert.pem 与隧道凭证。

### 已完成的操作（可复现）
1. 备份电商站源码：`cp -R <loveshop-grid> ~/backups/loveshop-grid-backup-20260822`
2. 写 `~/.cloudflared/config.yml`：
   ```yaml
   tunnel: 95c740e4-22f8-45b5-862d-49d638c1f817
   credentials-file: /Users/like/.cloudflared/95c740e4-22f8-45b5-862d-49d638c1f817.json
   ingress:
     - hostname: loveshop.us.ci
       service: http://localhost:8000
     - hostname: www.loveshop.us.ci
       service: http://localhost:8000
     - service: http_status:404
   ```
3. DNS 覆盖（原 Pages 的 CNAME 被替换）：
   ```bash
   cloudflared tunnel route dns -f ai-media-api loveshop.us.ci
   cloudflared tunnel route dns -f ai-media-api www.loveshop.us.ci
   ```
4. 启动隧道：`cloudflared tunnel --config ~/.cloudflared/config.yml run ai-media-api`
5. 启动后端：`cd ai-media-pipeline && ./run-local-api.sh`（或 uvicorn，需 `RENDER_VIDEO=1` 和 Chrome 路径）
6. 验证：`https://loveshop.us.ci` 返回登录页；密码 `victory`；`/api/accounts` 未登录 401；公网提交选题生成出 `output.mp4`。

### 关键约束
- **后端与隧道都跑在本地 Mac**，Mac 睡眠/关机/进程退出 → 网站 503。需长期挂着请配 launchd 自动拉起（见末尾）。
- 根域名已不再服务 loveshop-grid 电商站（源码已备份，可在 Cloudflare 面板把 Pages 项目重新绑回 `loveshop.us.ci` 回滚）。

---

本控制台前端由 FastAPI 后端直接托管 `web-console/`（同源 `const API=""`），无构建步骤。
路径 A~D 是历史候选方案（静态 Pages / Git 部署），因后端需在本地运行，最终落地为上面的隧道方案。

> 旧前提：Cloudflare API token（cfat_3DSy…）失效导致面板上传被卡；隧道方案用 cloudflared 凭证，不依赖该 token。

---

## 路径 A：子域名 tools.loveshop.us.ci（推荐，不碰现有电商站）

1. 打开 Cloudflare 面板 → **Workers & Pages** → **Create** → **Pages** → **Upload assets**。
2. 拖入 `web-console/` 整个文件夹，项目名填 `ai-media-console`。
3. 部署完成后进入项目 → **Custom domains** → 添加 `tools.loveshop.us.ci`。
4. 按提示在 DNS 添加一条 CNAME（Cloudflare 会给出值），等生效。
5. 访问 `https://tools.loveshop.us.ci` 即可。

> 根域名 `loveshop.us.ci` 继续由 loveshop-grid 电商站使用，互不影响。

---

## 路径 B：根域名 loveshop.us.ci（你要的“主域名上”，⚠️ 会覆盖电商站）

> ⚠️ **破坏性警告**：`loveshop.us.ci` 当前绑定在 loveshop-grid 电商站项目上。若把根域名绑到这个控制台 Pages 项目，**原电商站将不再通过该域名访问**（除非你另行保留/回滚）。请先确认：
> - 已导出或备份 loveshop-grid 的源码/构建产物；
> - 你确实要用控制台替换店铺首页（或店铺已迁到别处）。

1. 打开 Cloudflare 面板 → **Workers & Pages** → **Create** → **Pages** → **Upload assets**。
2. 拖入 `web-console/` 文件夹，项目名填 `ai-media-console`。
3. 部署完成后进入项目 → **Custom domains** → 添加 `loveshop.us.ci`。
4. Cloudflare 会提示该域名已被另一 Pages 项目占用 → 确认**移除原绑定**并改绑到本项目。
5. 等待 DNS/SSL 生效（通常几分钟），访问 `https://loveshop.us.ci` 即为控制台。

如需回滚：在原 loveshop-grid 项目重新绑定 `loveshop.us.ci` 即可。

---

## 路径 C：Git 自动部署（push 即上线，推荐）

> 需你在 GitHub 有账号并把本仓库推送上去；Cloudflare 侧在面板**连接 Git**（token 失效不影响 Git 连接，授权用 GitHub OAuth 而非 API token）。仓库根已是 `ai-media-pipeline`，`.gitignore` 已排除 `workspace/` 与本地密钥。

1. GitHub 新建一个空仓库（如 `ai-media-pipeline`），**不要**勾选自动生成 README / .gitignore。
2. 本机添加远程并推送（替换 `<你>` / `<仓库名>`）：
   ```bash
   cd ai-media-pipeline
   git remote add origin https://github.com/<你>/<仓库名>.git
   git branch -M main
   git push -u origin main
   ```
3. Cloudflare 面板 → **Workers & Pages** → **Create** → **Pages** → **Connect to Git** → 授权 GitHub → 选中该仓库。
4. 构建设置（关键）：
   - **Framework preset：None**（纯静态，无框架）
   - **Build command：留空**
   - **Output directory：`web-console`**
   - 其余默认 → **Save and Deploy**。
5. 部署完成后，**Custom domains** 绑定 `loveshop.us.ci`（路径 B 的覆盖说明同样适用）或 `tools.loveshop.us.ci`（保留店铺）。
6. 之后每次 `git push` 自动重新部署，无需再拖文件夹。

---

## 路径 D：本地后端直接托管控制台（当前最稳，无需隧道）

> 受本机网络/代理限制，ngrok / cloudflared 等隧道在该设备上无法稳定暴露本地后端。最简单可靠的方案是：FastAPI 后端启动后**直接托管** `web-console/`，访问 `http://localhost:8000` 即可一键生成。

### 启动

```bash
cd ai-media-pipeline
./run-local-api.sh
# 或手动：
# cd api && source venv/bin/activate && python server.py
```

### 使用

1. 浏览器打开 `http://localhost:8000`。
2. 在「⑦ 一键生成视频」选择账号、步骤、话题，点按钮。
3. 后端在本地跑完整条流水线；状态、日志、产物在页面实时刷新。

### 远程/手机访问（可选）

如需从其他设备访问，可继续尝试：
- `ngrok http 127.0.0.1:8000`（当前在本机因代理限制处于 offline，可换网络再试）。
- `cloudflared tunnel --url http://127.0.0.1:8000`（本机 7844/443 被防火墙拦截）。
- 成功后把隧道地址填到控制台「后端 API 地址」输入框（会自动保存）。

---

## 路径 E：Cloudflare Containers 全链路一键（前端 Pages + 后端 Container）

> 满足“部署到网站 + 一键生成视频”：前端静态站部署在 loveshop.us.ci（Pages），后端 FastAPI 跑在 Cloudflare Containers 执行整条流水线（含爬取→脚本→配音→Remotion 渲染→分发清单）。
> ⚠️ Containers 当前基于 **Durable Object** 模型（不是早期 beta）；本机需 **Docker 在运行** + 账号开启 Containers 权限；`wrangler login` 走 GitHub OAuth，不受 API token 失效影响。

### 后端文件（已按 2026 Container API 重写）
- `api/server.py`：FastAPI，POST `/api/generate`、GET `/api/job/<id>`、GET `/api/file`、GET `/api/health`。
- `Dockerfile`（**仓库根**）：python3.12 + node20 + ffmpeg，构建上下文=仓库根，`COPY . /app` 复制完整仓库。
- `.dockerignore`：排除 `.git` / `workspace` / `node_modules` 等。
- `api/worker.js`：继承 `Container` 类的 Worker，把 `/api/*` 代理给 Container（defaultPort 8000）。
- `wrangler.toml`（**仓库根**）：`containers` + `durable_objects` 绑定 + `migrations` 配置。
- 默认 `RENDER_VIDEO=0`（不渲染）；装好 Remotion 并设 `RENDER_VIDEO=1` 才出 mp4。

### 本机前置（一次性）
1. 安装 wrangler：`npm install -g wrangler`（或 `brew install wrangler`）
2. 安装并启动 **Docker Desktop**，`docker info` 确认 daemon 在跑（首部署必须用 Docker 构建镜像）
3. `wrangler login` → GitHub OAuth 授权

### 部署
```bash
cd ai-media-pipeline          # 仓库根（wrangler.toml 在此）
npx wrangler deploy
# 首次构建+推送镜像较慢；部署后等几分钟容器就绪
```
部署后在面板 **Workers & Pages → Containers** 看状态/日志。

### 让前端调到后端（推荐同域路由，无 CORS）
Cloudflare 面板 → `loveshop.us.ci` 域名 → **Workers 路由** → 添加：
- 路由：`loveshop.us.ci/api/*`
- 服务：`ai-media-worker`
前端 `API_BASE` 留空（同域 `/api`），无需改代码。

### 全链路真正出片前提（后端环境准备）
- MediaCrawler 工程 + 登录态 cookies（爬取步骤）。
- PyVideoTrans 路径（字幕配音）。
- Remotion 工程 `npm install` 就绪 + `RENDER_VIDEO=1`（出片；默认 0 只产出脚本/素材）。
- ffmpeg（Dockerfile 已装）。

### 验证
```bash
curl https://loveshop.us.ci/api/health   # 应返回 {"status":"ok",...}
```
控制台点「⑦ 一键生成视频」→ 填账号+话题 → 看进度 → 视频就绪即内嵌播放。

---

## 本地预览（部署前自测）

```bash
cd ai-media-pipeline/web-console
python3 -m http.server 4173
# 浏览器打开 http://localhost:4173
```

## 更新上线

改完 `index.html` / `assets/*` 后，回 Cloudflare 面板该 Pages 项目 → **Upload assets** 重新拖入 `web-console/` 文件夹即可（或连 Git 后自动构建）。

---

## 开机自启（launchd）：让站点在 Mac 重启/登录后自动恢复

隧道和后端都跑在本地，Mac 重启后会停。用 launchd 让两者随登录自动拉起（避免网站 503）。

### 1) 后端 `~/Library/LaunchAgents/com.loveshop.aimedia.plist`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
  <key>Label</key><string>com.loveshop.aimedia</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/like/.workbuddy/binaries/python/envs/default/bin/python</string>
    <string>-m</string><string>uvicorn</string>
    <string>api.server:app</string>
    <string>--host</string><string>0.0.0.0</string><string>--port</string><string>8000</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/like/WorkBuddy/2026-08-21-10-49-01/ai-media-pipeline</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>RENDER_VIDEO</key><string>1</string>
    <key>REMOTION_CHROME_EXECUTABLE_PATH</key><string>/Applications/Google Chrome.app/Contents/MacOS/Google Chrome</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/like/WorkBuddy/2026-08-21-10-49-01/ai-media-pipeline/launchd-backend.log</string>
  <key>StandardErrorPath</key><string>/Users/like/WorkBuddy/2026-08-21-10-49-01/ai-media-pipeline/launchd-backend.log</string>
</dict>
</plist>
```

### 2) 隧道 `~/Library/LaunchAgents/com.loveshop.tunnel.plist`
`ProgramArguments` 改为：
`/opt/homebrew/bin/cloudflared` `tunnel` `--config` `/Users/like/.cloudflared/config.yml` `run` `ai-media-api`
其余同上（`RunAtLoad`/`KeepAlive`/`StandardOutPath` 指向 `launchd-tunnel.log`）。

### 3) 加载
```bash
launchctl load ~/Library/LaunchAgents/com.loveshop.aimedia.plist
launchctl load ~/Library/LaunchAgents/com.loveshop.tunnel.plist
# 卸载：launchctl unload ~/Library/LaunchAgents/com.loveshop.*.plist
```
> 加载前请先停掉手动起的 uvicorn / cloudflared，避免 8000 端口或隧道重复连接冲突。
