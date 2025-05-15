#!/bin/bash

# Delay for 20 seconds
sleep 30

# Source nvm script to make nvm command available
export NVM_DIR="$HOME/.nvm"
# This loads nvm
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Change directory to the backend folder
cd ~/Desktop/recognition/recognition-parent/backend &
cd ~/Desktop/recognition/recognition-parent &
cd ~/Desktop/recognition/recognition-parent/backend 

# Start the Node.js server
nvm use 16

/opt/homebrew/bin/node server.js &

# Wait for 5 seconds
sleep 5

# Change directory to the frontend build directory
cd ~/Desktop/recognition/recognition-parent/frontend/dist/

# Open the main.app
open recognition.app