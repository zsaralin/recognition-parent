#!/bin/bash

# Delay for 20 seconds
sleep 20

# Change directory to the backend folder
cd ~/Desktop/recognition/recognition-parent/backend &
cd ~/Desktop/recognition/recognition-parent &
cd ~/Desktop/recognition/recognition-parent/backend

# Start the Node.js server
/opt/homebrew/bin/node server.js &

# Wait for 5 seconds
sleep 5

# Change directory to the frontend build directory
cd ~/Desktop/recognition/recognition-parent/frontend/dist/

# Open the main.app
open recognition.app