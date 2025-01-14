#!/bin/sh

# Start backend
cd /app/backend
node server.js &

# Start frontend
cd /app/frontend
npm run preview &

# Keep container running
wait