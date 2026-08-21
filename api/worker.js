// Cloudflare Containers 代理 Worker（2026 当前 API：Container 继承 Durable Object）
// 职责：把 /api/* 请求转发给后端 Container（跑 FastAPI，监听 8000）。
// 其余路径返回 404（前端由 Pages 提供）。
import { Container } from "cloudflare:containers";

export class AiMediaContainer extends Container {
  defaultPort = 8000;
  // 空闲 30 分钟后休眠，省资源；下次请求会自动唤醒（首请求稍慢）
  sleepAfter = "30m";
  envVars = {
    RENDER_VIDEO: "0",
    PORT: "8000",
  };
  async onStart() {
    console.log("ai-media container started");
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith("/api")) {
      return new Response("not found", { status: 404 });
    }
    // 固定实例 id "shared"：复用同一容器，保证 job 产物目录持久可访问
    const container = env.AI_MEDIA_CONTAINER.getByName("shared");
    return container.fetch(request);
  },
};
