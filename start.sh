#!/bin/bash

# backend
echo "Starting backend..."
python main.py &
BACKEND_PID=$!

sleep 2

# frontend
echo "Starting frontend..."
cd frontend && npm run dev &
FRONTEND_PID=$!


echo "Press any key to stop servers..."
read -n 1


kill $BACKEND_PID
kill $FRONTEND_PID