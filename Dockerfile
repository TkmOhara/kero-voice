# syntax=docker/dockerfile:1.4
FROM nvidia/cuda:12.8.0-base-ubuntu24.04

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    curl ca-certificates ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"
ENV UV_CACHE_DIR=/root/.cache/uv
ENV UV_LINK_MODE=copy

# uv.lockファイルがあればコピー（キャッシュ効率向上）
COPY .python-version pyproject.toml uv.lock* /app/

# BuildKitキャッシュマウントでuvのダウンロードキャッシュを永続化
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

CMD ["uv", "run", "./src/main.py"]