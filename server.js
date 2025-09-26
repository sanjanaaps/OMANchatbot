#!/usr/bin/env node
/**
 * Node.js API Server for Central Bank of Oman Chatbot
 * Acts as a proxy between React frontend and Flask backend
 */

const express = require('express');
const cors = require('cors');
const axios = require('axios');
const multer = require('multer');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
require('dotenv').config();

const app = express();
const PORT = process.env.NODE_PORT || 3001;
const FLASK_BACKEND_URL = process.env.FLASK_BACKEND_URL || 'http://localhost:5000';

// Security middleware
app.use(helmet());
app.use(cors({
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    credentials: true
}));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100 // limit each IP to 100 requests per windowMs
});
app.use(limiter);

// Body parsing middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Configure multer for file uploads
const storage = multer.memoryStorage();
const upload = multer({ 
    storage: storage,
    limits: {
        fileSize: 10 * 1024 * 1024 // 10MB limit
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ 
        status: 'OK', 
        timestamp: new Date().toISOString(),
        backend: FLASK_BACKEND_URL
    });
});

// Authentication endpoints
app.post('/api/auth/login', async (req, res) => {
    try {
        const response = await axios.post(`${FLASK_BACKEND_URL}/login`, req.body, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });
        
        // Extract session cookie from Flask response
        const setCookieHeader = response.headers['set-cookie'];
        if (setCookieHeader) {
            res.set('Set-Cookie', setCookieHeader);
        }
        
        res.json(response.data);
    } catch (error) {
        console.error('Login error:', error.response?.data || error.message);
        res.status(error.response?.status || 500).json({
            error: 'Login failed',
            message: error.response?.data?.message || error.message
        });
    }
});

app.post('/api/auth/logout', async (req, res) => {
    try {
        const response = await axios.post(`${FLASK_BACKEND_URL}/logout`, {}, {
            headers: {
                'Cookie': req.headers.cookie
            }
        });
        
        // Clear session cookie
        res.clearCookie('session');
        res.json({ message: 'Logged out successfully' });
    } catch (error) {
        console.error('Logout error:', error.response?.data || error.message);
        res.status(error.response?.status || 500).json({
            error: 'Logout failed',
            message: error.response?.data?.message || error.message
        });
    }
});

// Dashboard endpoint
app.get('/api/dashboard', async (req, res) => {
    try {
        const response = await axios.get(`${FLASK_BACKEND_URL}/dashboard`, {
            headers: {
                'Cookie': req.headers.cookie
            }
        });
        res.json(response.data);
    } catch (error) {
        console.error('Dashboard error:', error.response?.data || error.message);
        res.status(error.response?.status || 500).json({
            error: 'Failed to fetch dashboard data',
            message: error.response?.data?.message || error.message
        });
    }
});

// Chat endpoints
app.get('/api/chat', async (req, res) => {
    try {
        const response = await axios.get(`${FLASK_BACKEND_URL}/chat`, {
            headers: {
                'Cookie': req.headers.cookie
            }
        });
        res.json(response.data);
    } catch (error) {
        console.error('Chat GET error:', error.response?.data || error.message);
        res.status(error.response?.status || 500).json({
            error: 'Failed to fetch chat data',
            message: error.response?.data?.message || error.message
        });
    }
});

app.post('/api/chat', async (req, res) => {
    try {
        const response = await axios.post(`${FLASK_BACKEND_URL}/chat`, req.body, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Cookie': req.headers.cookie
            }
        });
        res.json(response.data);
    } catch (error) {
        console.error('Chat POST error:', error.response?.data || error.message);
        res.status(error.response?.status || 500).json({
            error: 'Failed to send message',
            message: error.response?.data?.message || error.message
        });
    }
});

// Documents endpoints
app.get('/api/documents', async (req, res) => {
    try {
        const response = await axios.get(`${FLASK_BACKEND_URL}/documents`, {
            headers: {
                'Cookie': req.headers.cookie
            }
        });
        res.json(response.data);
    } catch (error) {
        console.error('Documents error:', error.response?.data || error.message);
        res.status(error.response?.status || 500).json({
            error: 'Failed to fetch documents',
            message: error.response?.data?.message || error.message
        });
    }
});

// Upload endpoint
app.post('/api/upload', upload.single('file'), async (req, res) => {
    try {
        const formData = new FormData();
        if (req.file) {
            formData.append('file', req.file.buffer, {
                filename: req.file.originalname,
                contentType: req.file.mimetype
            });
        }

        const response = await axios.post(`${FLASK_BACKEND_URL}/upload`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
                'Cookie': req.headers.cookie
            }
        });
        res.json(response.data);
    } catch (error) {
        console.error('Upload error:', error.response?.data || error.message);
        res.status(error.response?.status || 500).json({
            error: 'Upload failed',
            message: error.response?.data?.message || error.message
        });
    }
});

// Voice endpoints
app.post('/api/voice/start', async (req, res) => {
    try {
        const response = await axios.post(`${FLASK_BACKEND_URL}/voice/start`, req.body, {
            headers: {
                'Content-Type': 'application/json',
                'Cookie': req.headers.cookie
            }
        });
        res.json(response.data);
    } catch (error) {
        console.error('Voice start error:', error.response?.data || error.message);
        res.status(error.response?.status || 500).json({
            error: 'Failed to start voice recording',
            message: error.response?.data?.message || error.message
        });
    }
});

app.post('/api/voice/transcribe', upload.single('audio'), async (req, res) => {
    try {
        const formData = new FormData();
        if (req.file) {
            formData.append('audio', req.file.buffer, {
                filename: req.file.originalname,
                contentType: req.file.mimetype
            });
        }

        const response = await axios.post(`${FLASK_BACKEND_URL}/voice/transcribe`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
                'Cookie': req.headers.cookie
            }
        });
        res.json(response.data);
    } catch (error) {
        console.error('Voice transcribe error:', error.response?.data || error.message);
        res.status(error.response?.status || 500).json({
            error: 'Failed to transcribe audio',
            message: error.response?.data?.message || error.message
        });
    }
});

// Error handling middleware
app.use((error, req, res, next) => {
    console.error('Unhandled error:', error);
    res.status(500).json({
        error: 'Internal server error',
        message: 'An unexpected error occurred'
    });
});

// 404 handler
app.use('*', (req, res) => {
    res.status(404).json({
        error: 'Not found',
        message: 'The requested endpoint does not exist'
    });
});

// Start server
app.listen(PORT, () => {
    console.log(`🚀 Node.js API Server running on port ${PORT}`);
    console.log(`📡 Proxying requests to Flask backend: ${FLASK_BACKEND_URL}`);
    console.log(`🌐 Frontend URL: ${process.env.FRONTEND_URL || 'http://localhost:3000'}`);
});

module.exports = app;
