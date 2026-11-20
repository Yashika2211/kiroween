#!/bin/sh
# Start the sandbox Docker daemon (state on the persistent volume), then the API.
# dockerd-entrypoint.sh sets up cgroup v2 nesting when this itself runs in a container.
set -eu
mkdir -p /data/docker /data/workspaces
DOCKER_TLS_CERTDIR="" dockerd-entrypoint.sh dockerd --data-root /data/docker --host unix:///var/run/docker.sock >/var/log/dockerd.log 2>&1 &
for i in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 1; done
docker info >/dev/null 2>&1 || { echo "dockerd failed to start"; tail -50 /var/log/dockerd.log; exit 1; }
# Warm the sandbox image so the first autopsy is fast.
docker image inspect "${NECRO_SANDBOX_IMAGE:-python:3.12-slim}" >/dev/null 2>&1 \
  || docker pull -q "${NECRO_SANDBOX_IMAGE:-python:3.12-slim}" || true
exec uv run --no-dev uvicorn necromancer.api.app:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
