# Cloudflare Containers 镜像：跑 ai-media-pipeline 后端（FastAPI）
# 构建上下文 = 仓库根（wrangler.toml 在此），COPY . /app 复制完整仓库（pipeline/config/video/web-console）。
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    RENDER_VIDEO=0

# 系统依赖 + ffmpeg + node 20（Remotion 渲染用）
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg curl ca-certificates gnupg git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装 Python 依赖（利用层缓存）
COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt

# 拷贝整个仓库（pipeline / video / config / web-console 都带上）
COPY . /app

WORKDIR /app/api
EXPOSE 8000
CMD ["sh", "-c", "python server.py"]
