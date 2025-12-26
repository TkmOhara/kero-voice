FROM nvidia/cuda:12.8.0-base-ubuntu24.04

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    curl ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"

COPY .python-version pyproject.toml /app/

RUN uv sync

# RUN uv pip uninstall -y torch torchvision torchaudio || true

# RUN uv pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124

CMD ["uv", "run", "./src/main.py"]