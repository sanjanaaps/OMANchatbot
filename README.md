# Oman Central Bank - Department-Secure Document Analyzer & Chatbot

A Flask-based web application that provides secure document analysis and AI-powered chatbot functionality for different departments within the Oman Central Bank. Each user can only access documents from their assigned department, ensuring data confidentiality and security.

## 🚀 Features

### Core Functionality
- **Department-Secure Access**: Users can only view/search documents from their assigned department
- **Document Upload**: Support for PDF, DOCX, DOC, and image files (PNG, JPG, JPEG, TIFF)
- **Text Extraction**: Automatic text extraction from various file formats
- **AI Summarization**: Extractive summarization using TextRank algorithm
- **Local Search**: TF-IDF + cosine similarity search across department documents
- **AI Chatbot**: Gemini API integration with fallback for complex queries
- **Bilingual Support**: English and Arabic language support

### Security Features
- **Authentication**: bcrypt-hashed passwords with session management
- **Department Isolation**: Strict access control based on user department
- **Secure File Handling**: Server-side text extraction with file validation

## 🛠️ Tech Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Frontend**: HTML templates with TailwindCSS
- **Authentication**: bcrypt password hashing
- **Document Processing**: PyPDF2, pdfminer, python-docx, pytesseract
- **AI Integration**: Google Gemini API
- **Search**: TF-IDF with cosine similarity

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL (local or cloud instance)
- Google Gemini API key (for AI features)

## 🔧 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd oman-central-bank-doc-analyzer
```

### 2. Create Virtual Environment
```bash
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables
Create a `.env` file in the project root:
```env
# PostgreSQL Configuration
POSTGRES_URI=postgresql://postgres:1234@localhost:5432/doc_analyzer
DB_NAME=doc_analyzer

# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-here

# Gemini API Configuration
GEMINI_API_KEY=your-gemini-api-key-here

# Optional: Flask Environment
FLASK_ENV=development
```

### 5. Set Up Database
```bash
# Create database and tables
python migrate_to_postgres.py

# Seed with test users
python seed_users.py
```

This will create the database tables and seed 5 test users:
- `finance_user` / `finance123` (Finance)
- `policy_user` / `policy123` (Monetary Policy & Banking)
- `currency_user` / `currency123` (Currency)
- `legal_user` / `legal123` (Legal & Compliance)
- `itfinance_user` / `itfinance123` (IT / Finance)

### 6. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 🏗️ Project Structure

```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── seed_users.py         # Database seeding script
├── README.md             # This file
├── lib/                  # Core modules
│   ├── db.py            # Database operations
│   ├── auth.py          # Authentication utilities
│   ├── extract.py       # Document text extraction
│   ├── search.py        # TF-IDF search implementation
│   └── gemini.py        # Gemini API integration
├── templates/            # HTML templates
│   ├── base.html        # Base template
│   ├── login.html       # Login page
│   ├── dashboard.html   # User dashboard
│   ├── upload.html      # Document upload
│   ├── upload_success.html # Upload confirmation
│   ├── search.html      # Document search
│   ├── chat.html        # AI chatbot interface
│   └── documents.html   # Document listing
├── static/              # Static assets (CSS, JS, images)
└── uploads/             # Uploaded files directory
```

## 🔐 Security Considerations

### Production Hardening (TODOs)
- [ ] Use environment-specific configuration files
- [ ] Implement rate limiting for API endpoints
- [ ] Add CSRF protection
- [ ] Use HTTPS in production
- [ ] Implement proper logging and monitoring
- [ ] Add input validation and sanitization
- [ ] Use secure file storage (not local filesystem)
- [ ] Implement backup and disaster recovery
- [ ] Add audit logging for document access
- [ ] Use PostgreSQL authentication and authorization

### Current Security Features
- ✅ bcrypt password hashing
- ✅ Session-based authentication
- ✅ Department-based access control
- ✅ File type validation
- ✅ Secure file upload handling

## 🎯 Usage

### 1. Login
Use one of the test user credentials to log in to the system.

### 2. Upload Documents
- Navigate to the Upload page
- Select a supported file format
- The system will automatically extract text and generate a summary

### 3. Search Documents
- Use the Search page to find documents in your department
- Local search uses TF-IDF with cosine similarity
- AI fallback is triggered for low-scoring results

### 4. Chat with AI Assistant
- Ask questions about your department's documents
- The AI can only access information from your department
- Supports both English and Arabic responses

### 5. View Documents
- Browse all documents in your department
- View document details and metadata

## 🔧 Configuration

### PostgreSQL Configuration
```python
POSTGRES_URI = "postgresql://postgres:1234@localhost:5432/doc_analyzer"  # Local PostgreSQL
# or
POSTGRES_URI = "postgresql://user:pass@host:5432/doc_analyzer"  # Production PostgreSQL
```

### Gemini API Setup
1. Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Set the `GEMINI_API_KEY` environment variable
3. The application will automatically use the API for AI features

### File Upload Limits
- Maximum file size: 16MB
- Supported formats: PDF, DOCX, DOC, PNG, JPG, JPEG, TIFF
- Files are stored locally in the `uploads/` directory

## 🧪 Testing

### Manual Testing
1. Test user login with different departments
2. Upload various file formats
3. Verify department isolation (users can't access other departments' data)
4. Test search functionality
5. Test AI chatbot responses

### Automated Testing
```bash
pytest tests/
```

## 🚀 Deployment

### Development
```bash
python app.py
```

### Production
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker (Optional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## 📊 API Endpoints

### Authentication
- `GET /` - Redirect to login or dashboard
- `GET /login` - Login page
- `POST /login` - Process login
- `GET /logout` - Logout user

### Document Management
- `GET /dashboard` - User dashboard
- `GET /upload` - Upload page
- `POST /upload` - Process file upload
- `GET /documents` - List department documents

### Search & AI
- `GET /search` - Search page
- `POST /search` - Process search query
- `GET /chat` - Chat interface
- `POST /chat` - Process chat message
- `POST /translate` - Translate text

## 🐛 Troubleshooting

### Common Issues

1. **PostgreSQL Connection Error**
   - Ensure PostgreSQL is running
   - Check POSTGRES_URI environment variable
   - Verify the database 'doc_analyzer' exists
   - Verify network connectivity

2. **Gemini API Errors**
   - Verify GEMINI_API_KEY is set correctly
   - Check API quota and billing
   - Ensure internet connectivity

3. **File Upload Issues**
   - Check file size limits (16MB)
   - Verify file format is supported
   - Ensure uploads directory has write permissions

4. **Text Extraction Failures**
   - Install required system dependencies (Tesseract for OCR)
   - Check file corruption
   - Verify file format compatibility

### Logs
Application logs are written to the console. In production, configure proper logging to files.

## 📝 License

This project is developed for the Oman Central Bank. All rights reserved.

## 🤝 Contributing

This is an internal project for the Oman Central Bank. For contributions or modifications, please contact the development team.

## 📞 Support

For technical support or questions, please contact the IT department at the Oman Central Bank.

---

**Note**: This is a proof-of-concept implementation. For production deployment, additional security measures, monitoring, and hardening are required as outlined in the TODOs section.
