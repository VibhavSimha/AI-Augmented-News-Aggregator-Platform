#!/bin/bash
# Start RAG system with worker and main app

set -e

cd "$(dirname "$0")"

echo "========================================="
echo "Starting RAG System"
echo "========================================="

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found at ./venv"
    echo "Please create a virtual environment first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Check if data files exist
if [ ! -f "data/news.index" ] || [ ! -f "data/news_meta.parquet" ]; then
    echo "❌ RAG data files not found in data/"
    echo "Please run the data preparation scripts first:"
    echo "  cd scripts"
    echo "  python download_gdelt_dataset.py"
    echo "  python build_rag_index.py"
    exit 1
fi

# Kill existing processes on ports 5000 and 5001
echo ""
echo "Stopping any existing servers..."
lsof -ti:5000 | xargs kill -9 2>/dev/null || true
lsof -ti:5001 | xargs kill -9 2>/dev/null || true
sleep 2

# Start RAG worker
echo ""
echo "========================================="
echo "Starting RAG Worker (port 5001)..."
echo "========================================="
./venv/bin/python -u rag_worker.py > rag_worker.log 2>&1 &
WORKER_PID=$!
echo "RAG Worker PID: $WORKER_PID"

# Wait for worker to be ready
echo "Waiting for RAG worker to initialize..."
sleep 15

# Check if worker is healthy
WORKER_HEALTH=$(curl -s http://127.0.0.1:5001/health 2>/dev/null || echo "failed")
if echo "$WORKER_HEALTH" | grep -q '"rag_ready":true'; then
    echo "✓ RAG Worker is healthy"
else
    echo "❌ RAG Worker failed to start"
    echo "Check rag_worker.log for details"
    kill $WORKER_PID 2>/dev/null || true
    exit 1
fi

# Start main Flask app
echo ""
echo "========================================="
echo "Starting Main App (port 5000)..."
echo "========================================="
./venv/bin/python -u app.py > app.log 2>&1 &
APP_PID=$!
echo "Main App PID: $APP_PID"

# Wait for app to be ready
echo "Waiting for main app to initialize..."
sleep 5

# Check if app is healthy
APP_HEALTH=$(curl -s http://127.0.0.1:5000/health 2>/dev/null || echo "failed")
if echo "$APP_HEALTH" | grep -q '"ok":true'; then
    echo "✓ Main App is healthy"
else
    echo "❌ Main App failed to start"
    echo "Check app.log for details"
    kill $WORKER_PID $APP_PID 2>/dev/null || true
    exit 1
fi

# Success
echo ""
echo "========================================="
echo "✓ RAG System Started Successfully"
echo "========================================="
echo ""
echo "Services:"
echo "  RAG Worker:  http://127.0.0.1:5001 (PID: $WORKER_PID)"
echo "  Main App:    http://127.0.0.1:5000 (PID: $APP_PID)"
echo ""
echo "Logs:"
echo "  Worker: tail -f rag_worker.log"
echo "  App:    tail -f app.log"
echo ""
echo "To stop:"
echo "  kill $WORKER_PID $APP_PID"
echo "  # or"
echo "  lsof -ti:5000 | xargs kill -9"
echo "  lsof -ti:5001 | xargs kill -9"
echo ""
echo "Frontend: Open client/index.html or run 'cd client && npm run dev'"
echo ""
