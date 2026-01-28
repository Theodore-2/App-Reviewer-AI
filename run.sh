#!/bin/bash

# App Reviewer AI - Unified Run Script

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting App Reviewer AI...${NC}"

# 0. Cleanup existing processes on ports 8000 and 3000
echo -e "${BLUE}🧹 Cleaning up existing processes on ports 8000 and 3000...${NC}"
lsof -ti :8000,3000 | xargs kill -9 2>/dev/null || true

# 1. Setup Backend Environment
echo -e "${GREEN}📦 Setting up Backend Environment...${NC}"
cd backend

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${BLUE}🔨 Creating virtual environment...${NC}"
    python3 -m venv venv
fi

source venv/bin/activate

# Install/Update requirements
echo -e "${BLUE}📥 Checking/Installing requirements...${NC}"
pip install -r requirements.txt

# Start Backend in the background
echo -e "${GREEN}🚀 Starting Backend API (Port 8000)...${NC}"
# Run uvicorn in background
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# 2. Wait for backend to be ready
echo -e "${BLUE}⏳ Waiting for backend to initialize...${NC}"
sleep 3

# 3. Start Frontend
echo -e "${GREEN}💻 Starting Frontend Server (Port 3000)...${NC}"
cd ../frontend
echo -e "${BLUE}🔗 Open your browser at: http://localhost:3000${NC}"
python3 -m http.server 3000

# Cleanup background process on exit
trap "kill $BACKEND_PID" EXIT
