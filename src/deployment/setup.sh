#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

pip3 install -r requirements.txt

if ! command -v docker &>/dev/null; then
    echo "Docker is not installed. Please install Docker and try again."
    exit 1
fi

if ! docker info &>/dev/null; then
    echo "Docker is not running. Please start Docker and try again."
    exit 1
fi

if curl -s http://localhost:6333/healthz >/dev/null 2>&1; then
    echo "Qdrant already running on port 6333."
else
    QDRANT_CONTAINER="qdrant_review"
    if docker ps -a --format '{{.Names}}' | grep -q "^${QDRANT_CONTAINER}$"; then
        docker start "$QDRANT_CONTAINER"
    else
        docker run -d --name "$QDRANT_CONTAINER" -p 6333:6333 qdrant/qdrant:latest
    fi
    echo "Waiting for Qdrant..."
    for i in $(seq 1 30); do
        if curl -s http://localhost:6333/healthz >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
fi

if pgrep -f "celery -A worker" >/dev/null 2>&1; then
    echo "Celery worker already running."
else
    celery -A worker worker --beat --loglevel=info --concurrency=1 &
    CELERY_PID=$!
    sleep 3
fi

if lsof -i :8080 >/dev/null 2>&1; then
    echo "Port 8080 already in use. Killing old server..."
    lsof -ti :8080 | xargs kill -9 2>/dev/null
    sleep 1
fi

echo "Starting web server on port 8080..."
echo "Open http://127.0.0.1:8080 in your browser."
echo "Press Ctrl+C to stop."

trap "echo 'Shutting down...'; kill $CELERY_PID 2>/dev/null; exit 0" INT TERM

python3 -m uvicorn app:app --host 0.0.0.0 --port 8080
