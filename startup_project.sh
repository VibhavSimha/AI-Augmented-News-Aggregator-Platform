#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Starting AI-Augmented News Aggregator${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to check if port is in use and kill process
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        echo -e "${YELLOW}Killing process on port $port (PID: $pid)${NC}"
        kill -9 $pid 2>/dev/null
        sleep 1
    fi
}

# Kill any existing processes on ports 5000 and 5001
echo -e "${YELLOW}Checking for existing processes...${NC}"
kill_port 5000
kill_port 5001
echo -e "${GREEN}✓ Ports cleaned${NC}"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo -e "${YELLOW}Please create a virtual environment first:${NC}"
    echo -e "  python3 -m venv venv"
    echo -e "  source venv/bin/activate"
    echo -e "  pip install -r requirements.txt"
    exit 1
fi

# Check if Python is available in venv
if [ ! -f "venv/bin/python3" ]; then
    echo -e "${RED}Error: Python not found in virtual environment!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Virtual environment found${NC}"
echo ""

# Start RAG Worker
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Starting RAG Worker (port 5001)...${NC}"
echo -e "${BLUE}=========================================${NC}"
./venv/bin/python3 rag_worker.py > rag_worker.log 2>&1 &
RAG_PID=$!
echo -e "${GREEN}RAG Worker started (PID: $RAG_PID)${NC}"
echo ""

# Wait for RAG worker to initialize
echo -e "${YELLOW}Waiting for RAG worker to initialize...${NC}"
sleep 3

# Check RAG worker health
for i in {1..20}; do
    if curl -s http://127.0.0.1:5001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ RAG Worker is healthy${NC}"
        break
    fi
    if [ $i -eq 20 ]; then
        echo -e "${RED}✗ RAG Worker failed to start${NC}"
        echo -e "${YELLOW}Check rag_worker.log for details${NC}"
        kill $RAG_PID 2>/dev/null
        exit 1
    fi
    sleep 2
    echo -e "${YELLOW}Still waiting... ($i/20)${NC}"
done
echo ""

# Start Main App
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Starting Main App (port 5000)...${NC}"
echo -e "${BLUE}=========================================${NC}"
./venv/bin/python3 app.py > app.log 2>&1 &
APP_PID=$!
echo -e "${GREEN}Main App started (PID: $APP_PID)${NC}"
echo ""

# Wait for main app to initialize
echo -e "${YELLOW}Waiting for main app to initialize...${NC}"
sleep 3

# Check main app health
for i in {1..15}; do
    if curl -s http://127.0.0.1:5000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Main App is healthy${NC}"
        break
    fi
    if [ $i -eq 15 ]; then
        echo -e "${RED}✗ Main App failed to start${NC}"
        echo -e "${YELLOW}Check app.log for details${NC}"
        kill $APP_PID 2>/dev/null
        kill $RAG_PID 2>/dev/null
        exit 1
    fi
    sleep 2
    echo -e "${YELLOW}Still waiting... ($i/15)${NC}"
done
echo ""

# Success summary
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}✓ All services started successfully!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "${BLUE}Service Status:${NC}"
echo -e "  RAG Worker:  ${GREEN}http://127.0.0.1:5001${NC} (PID: $RAG_PID)"
echo -e "  Main App:    ${GREEN}http://127.0.0.1:5000${NC} (PID: $APP_PID)"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo -e "  RAG Worker:  ${YELLOW}tail -f rag_worker.log${NC}"
echo -e "  Main App:    ${YELLOW}tail -f app.log${NC}"
echo ""
echo -e "${BLUE}To stop services:${NC}"
echo -e "  ${YELLOW}kill $RAG_PID $APP_PID${NC}"
echo -e "  or run: ${YELLOW}lsof -ti:5000,5001 | xargs kill${NC}"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
