#!/bin/bash

# AI Recruiting Agent - Local Run Script

echo "Starting AI Recruiting Agent..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install backend dependencies
echo "Installing backend dependencies..."
cd backend
pip install -r requirements.txt
cd ..

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
pip install -r requirements.txt
cd ..

# Start backend in background
echo "Starting backend API on http://localhost:8000..."
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting frontend UI on http://localhost:8501..."
cd frontend
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0 &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================="
echo "AI Recruiting Agent is running!"
echo "========================================="
echo "Backend API: http://localhost:8000"
echo "Frontend UI: http://localhost:8501"
echo "API Docs: http://localhost:8000/docs"
echo "========================================="
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for user interrupt
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
