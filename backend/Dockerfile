# Necromancer API. Repository code is never run in this container: it starts sibling
# sandbox containers through the Docker socket mounted by docker-compose.
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates docker.io \
 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY necromancer ./necromancer
RUN uv sync --frozen --no-dev

ENV NECRO_DB_PATH=/data/necromancer.sqlite3 \
    NECRO_WORKSPACE_DIR=/data/workspaces \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "necromancer.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
