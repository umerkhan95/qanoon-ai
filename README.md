# FuzeAI Assistants

## A web-based chat interface for interacting with custom OpenAI assistants, featuring real-time streaming responses and an iMessage-style UI.

## Features
Real-time streaming responses
iMessage-style chat bubbles
Multiple AI assistants integration
Chat history sidebar
File upload capability
Conversation persistence
Tech Stack
Frontend: React 18 + Vite
Backend: Node.js + Express
API: OpenAI Assistants API
Styling: CSS3
Installation


### Clone repository
git clone <repository-url>
cd fuzeai-assistants

### Install frontend dependencies
cd frontend
npm install

### Install backend dependencies
cd ../backend
npm install

### Create .env in backend directory
echo "OPENAI_API_KEY=your_api_key_here\nPORT=5001" > .env

Usage

### Start backend
cd backend
node server.js

### Start frontend
npm run dev

### Access app at http://localhost:5173

## Project Structure

├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── App.css
│   ├── package.json
│   └── vite.config.js
└── backend/
    ├── server.js
    └── package.json


## API Integration
Court Decisions Assistant (asst_LR7yCF7UbaC9newAmtebxhOG)
Court Decision Analyst (asst_jMbBlFW5SKlVXXVefaKDnBfc)

## Development
Frontend runs on Vite dev server
Backend uses Express with OpenAI API integration
Real-time response streaming
Persistent chat threads
File upload handling

## Environment Variables

OPENAI_API_KEY=sk-xxx
PORT=5001

## License
MIT