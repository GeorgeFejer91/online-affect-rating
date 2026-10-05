#!/usr/bin/env bash
# Serve the repo root locally (supports HTTP range requests for the video).
# Open: http://localhost:8000/task/index.html?dim=fear
#   test near the end of the film: ...&start_time=780
cd "$(dirname "$0")/.." && exec npx --yes http-server -p "${PORT:-8000}" -c-1 .
