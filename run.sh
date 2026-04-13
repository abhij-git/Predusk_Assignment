#!/bin/bash

set -e  # exit on error

echo "🚀 Starting Predusk stack..."

# 1. Start Docker (Mac)
echo "🐳 Starting Docker..."
open --background -a Docker

# Wait until Docker is ready
echo "⏳ Waiting for Docker to be ready..."
until docker info >/dev/null 2>&1; do
  sleep 2
done
echo "✅ Docker is ready"

# 2. Start containers (Postgres + Redis)
echo "📦 Starting docker services..."
docker-compose up -d

# 3. Start backend (FastAPI)
echo "⚙️ Starting backend..."
cd backend
source .venv/bin/activate

# Run backend in background
uvicorn app.main:app --reload &
BACKEND_PID=$!

# 4. Start Celery worker
echo "🧵 Starting Celery worker..."
celery -A app.celery_app worker -l info &
CELERY_PID=$!

cd ..

# 5. Start frontend
echo "🌐 Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!

cd ..

echo "🎉 All services started!"
echo ""
echo "📍 Backend:  http://127.0.0.1:8000"
echo "📍 Frontend: http://localhost:5173 (or shown in terminal)"
echo ""
echo "🛑 To stop everything:"
echo "kill $BACKEND_PID $CELERY_PID $FRONTEND_PID"