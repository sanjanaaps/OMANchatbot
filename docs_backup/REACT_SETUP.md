# React.js Frontend Setup Guide

## Overview

The Central Bank of Oman Chatbot has been restructured with a modern React.js frontend and Node.js API layer:

- **React.js Frontend** (Port 3000): Modern, responsive UI
- **Node.js API Server** (Port 3001): API proxy and middleware
- **Flask Backend** (Port 5000): Core business logic and AI processing

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React.js      │    │   Node.js       │    │   Flask         │
│   Frontend      │◄──►│   API Server    │◄──►│   Backend       │
│   (Port 3000)   │    │   (Port 3001)   │    │   (Port 5000)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### Option 1: Automated Setup (Recommended)
```bash
# Install Node.js dependencies
npm install

# Install React dependencies
cd frontend
npm install
cd ..

# Start all servers
python start_servers.py
```

### Option 2: Manual Setup

#### 1. Install Dependencies
```bash
# Install Node.js API server dependencies
npm install

# Install React frontend dependencies
cd frontend
npm install
cd ..
```

#### 2. Start Servers (in separate terminals)

**Terminal 1 - Flask Backend:**
```bash
python run_app.py
```

**Terminal 2 - Node.js API Server:**
```bash
node server.js
```

**Terminal 3 - React Frontend:**
```bash
cd frontend
npm start
```

## Access Points

- **Frontend**: http://localhost:3000
- **API Server**: http://localhost:3001
- **Flask Backend**: http://localhost:5000

## Features

### React Frontend
- ✅ Modern, responsive UI with Tailwind CSS
- ✅ Authentication with context management
- ✅ Real-time chat interface
- ✅ Document upload with drag & drop
- ✅ Voice recording and transcription
- ✅ Protected routes and session management

### Node.js API Server
- ✅ CORS handling and security headers
- ✅ Rate limiting and request validation
- ✅ File upload handling
- ✅ Session cookie management
- ✅ Error handling and logging

### Flask Backend (API-only)
- ✅ FAQ integration with 57 Q&A pairs
- ✅ Document processing and analysis
- ✅ AI chat with multiple fallback systems
- ✅ Voice transcription with Whisper
- ✅ User authentication and authorization

## Configuration

### Environment Variables
Create a `config.env` file:
```env
NODE_PORT=3001
FLASK_BACKEND_URL=http://localhost:5000
FRONTEND_URL=http://localhost:3000
FLASK_SECRET_KEY=dev-secret-key-change-in-production
DB_NAME=doc_analyzer
```

### API Endpoints

#### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout

#### Chat
- `GET /api/chat` - Get chat history
- `POST /api/chat` - Send message
- `POST /api/voice/start` - Start voice recording
- `POST /api/voice/transcribe` - Transcribe audio

#### Documents
- `GET /api/documents` - List documents
- `POST /api/upload` - Upload document

#### Dashboard
- `GET /api/dashboard` - Get dashboard data

## Development

### Frontend Development
```bash
cd frontend
npm start          # Start development server
npm run build      # Build for production
npm test           # Run tests
```

### API Development
```bash
npm run dev        # Start with nodemon (auto-restart)
npm start          # Start production server
```

## Production Deployment

### Build Frontend
```bash
cd frontend
npm run build
```

### Environment Setup
```bash
# Set production environment variables
export NODE_ENV=production
export FLASK_ENV=production
```

### Start Production Servers
```bash
# Start Flask backend
python run_app.py

# Start Node.js API server
node server.js

# Serve React build (using a static server like nginx or serve)
npx serve -s frontend/build -l 3000
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 3000, 3001, and 5000 are available
2. **CORS errors**: Check that FRONTEND_URL is correctly set
3. **Session issues**: Verify cookie settings and domain configuration
4. **File uploads**: Check file size limits and allowed types

### Logs
- Flask backend: Check console output
- Node.js API: Check console output
- React frontend: Check browser console and terminal

## Migration from Flask Templates

The Flask backend has been modified to be API-only:
- Removed template rendering routes
- All UI functionality moved to React
- Session management maintained for API authentication
- FAQ integration preserved and enhanced

## Security Features

- ✅ Helmet.js for security headers
- ✅ CORS configuration
- ✅ Rate limiting
- ✅ Input validation
- ✅ File upload restrictions
- ✅ Session-based authentication
