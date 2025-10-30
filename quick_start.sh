#!/bin/bash
# Quick Start - RAG Worker System
# Run this to start the entire system

echo "╔════════════════════════════════════════════════════╗"
echo "║    AI News Aggregator - RAG Worker System         ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Check prerequisites
if [ ! -f "data/news.index" ]; then
    echo "❌ ERROR: RAG data files not found!"
    echo ""
    echo "Please build the RAG index first:"
    echo "  cd scripts"
    echo "  python download_gdelt_dataset.py"
    echo "  python build_rag_index.py"
    echo ""
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "❌ ERROR: Virtual environment not found!"
    echo ""
    echo "Please create and setup venv:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo ""
    exit 1
fi

# Start system
echo "Starting RAG system..."
./start_rag_system.sh

# Wait a moment
sleep 3

# Show quick reference
echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║              Quick Reference                       ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Services:"
echo "   Main App:    http://127.0.0.1:5000"
echo "   RAG Worker:  http://127.0.0.1:5001"
echo ""
echo "📋 Commands:"
echo "   Test:        ./test_worker_system.sh"
echo "   Worker Log:  tail -f rag_worker.log"
echo "   App Log:     tail -f app.log"
echo "   Stop All:    lsof -ti:5000 | xargs kill -9 && lsof -ti:5001 | xargs kill -9"
echo ""
echo "🔍 Health Checks:"
echo "   Worker:      curl http://127.0.0.1:5001/health"
echo "   Main App:    curl http://127.0.0.1:5000/health"
echo ""
echo "📚 Documentation:"
echo "   Full Guide:  RAG_WORKER_GUIDE.md"
echo "   Solution:    SOLUTION_COMPLETE.md"
echo ""
echo "✅ System ready! Open client/index.html or run 'cd client && npm run dev'"
echo ""
