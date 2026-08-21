# 部署 AI 自媒体控制台到 Cloudflare Pages

本控制台是**纯静态站点**（`web-console/` 目录），无构建步骤，可直接上传到 Cloudflare Pages。
它不能在线上执行 Python 流水线——只是命令生成 + 配置查看 + 流程参考，真实执行请在本机流水线目录跑命令。

> 前提：你的 Cloudflare API token（cfat_3DSy…）此前失效，自动化部署被卡，故走**面板手动上传**路径（无需 token）。

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

## 本地预览（部署前自测）

```bash
cd ai-media-pipeline/web-console
python3 -m http.server 4173
# 浏览器打开 http://localhost:4173
```

## 更新上线

改完 `index.html` / `assets/*` 后，回 Cloudflare 面板该 Pages 项目 → **Upload assets** 重新拖入 `web-console/` 文件夹即可（或连 Git 后自动构建）。
