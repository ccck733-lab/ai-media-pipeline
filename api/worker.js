// Cloudflare Containers 代理 Worker
// 职责：把 /api/* 请求转发给后端 Container（跑 FastAPI）。其余路径返回 404（前端由 Pages 提供）。
// 部署：在 api/ 目录 `wrangler deploy`（需 Containers beta 权限 + 登录 `wrangler login`）。
import { Container } from "node:container";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith("/api")) {
      return new Response("not found", { status: 404 });
    }
    // 取得（或创建）一个 Container 实例，把请求透传进去
    // beta API：get() 可带实例 id；此处用固定 id 复用同一实例
    const container = await env.ai_media.get("default");
    return container.fetch(request);
  },
};
