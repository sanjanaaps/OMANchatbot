# RAG Configuration Guide

## Overview

The Oman Central Bank Document Analyzer now supports optional RAG (Retrieval-Augmented Generation) functionality. You can choose to enable or disable RAG during startup, which allows you to:

- **Enable RAG**: Get advanced document-based question answering with AI models
- **Disable RAG**: Run the app without GPU requirements or heavy dependencies

## How to Start the App

### Option 1: With Configuration Prompt (Recommended)

```bash
python run_with_config.py
```

This will show you a configuration menu where you can choose whether to enable RAG.

### Option 2: Direct Start (RAG Disabled)

```bash
python app.py
```

This starts the app directly without RAG functionality.

### Option 3: Using Flask Command

```bash
flask run
```

This also starts without RAG functionality.

## RAG Requirements

If you choose to enable RAG, the following packages are required:

```bash
pip install -r requirements_rag.txt
```

**Required packages:**
- langchain
- transformers
- torch
- sentence-transformers
- faiss-cpu
- pdfplumber
- pytesseract
- Pillow
- deep-translator

## What Happens During Startup

### With Configuration Prompt:

1. **Console Prompt**: You'll see a menu asking if you want to enable RAG
2. **Dependency Check**: If you choose "yes", the system checks for required packages
3. **Installation Option**: If packages are missing, you can choose to install them automatically
4. **App Start**: The app starts with your chosen configuration

### Without Configuration Prompt:

1. **Default Mode**: App starts with RAG disabled
2. **No GPU/Heavy Dependencies**: No tensor loading or model downloading
3. **Core Functionality**: All basic features work (upload, search, chat, translation)

## Features Available

### With RAG Enabled:
- ✅ Advanced document-based Q&A
- ✅ Semantic search through documents
- ✅ AI-powered document analysis
- ✅ Vector-based similarity search
- ✅ All core features

### Without RAG (Default):
- ✅ Document upload and storage
- ✅ Local text search
- ✅ Gemini AI integration
- ✅ Chat functionality
- ✅ Translation services
- ✅ 10-point document summaries
- ❌ Advanced RAG features

## Configuration Files

- `run_with_config.py` - Main startup script with configuration prompt
- `startup_config.py` - Configuration logic and dependency checking
- `requirements_rag.txt` - RAG-specific dependencies
- `app_lib/rag_integration.py` - RAG implementation (only loaded if enabled)

## Troubleshooting

### RAG Dependencies Missing
```bash
pip install -r requirements_rag.txt
```

### GPU Issues
If you have GPU issues, you can still use RAG with CPU (slower but functional).

### Memory Issues
If you experience memory issues with RAG enabled, restart the app and choose "no" for RAG.

## Performance Notes

- **With RAG**: Higher memory usage, requires GPU for optimal performance
- **Without RAG**: Lightweight, fast startup, minimal resource usage
- **First-time RAG**: May take time to download models on first run

## Switching Between Modes

To switch between RAG enabled/disabled:
1. Stop the current app (Ctrl+C)
2. Run `python run_with_config.py`
3. Choose your preferred option
4. App restarts with new configuration
