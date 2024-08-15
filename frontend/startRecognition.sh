#!/bin/bash

# Delay for 20 seconds
sleep 20

# Change directory to the backend folder
cd ~/Desktop/recognition-2024-1/backend

# Start the Node.js server
node server.js &

# Wait for 5 seconds
sleep 5

# Change directory to the frontend build directory
cd ../frontend/build/dist/macOS

# Open the main.app
open main.app