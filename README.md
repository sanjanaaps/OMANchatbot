# Oman Central Bank - Department-Secure Document Analyzer & Chatbot

## 🔄 Recent Updates

### RAG (Retrieval-Augmented Generation) Integration
- Implemented advanced RAG system with FAISS-based similarity search
- Multi-format document support with OCR (PDF, PNG, JPG, JPEG, TIFF)
- Automatic translation between English and Arabic
- Department-aware document categorization
- Real-time document indexing and querying
- Intelligent response prioritization system

### Chat UI and Experience
- Session-based chat persistence
- Real-time message updates with AJAX
- Bilingual chat interface with timestamps
- Enhanced mobile responsiveness
- Progressive response system with fallbacks

### Deployment and Infrastructure
- Complete Apache production deployment system
- Systemd service management for Node.js and Flask
- Health monitoring and status endpoints
- Comprehensive logging and error handling
- SSL/HTTPS configuration with Let's Encrypt

### Security and Performance
- Strict department isolation and access control
- Enhanced user session management
- Audit logging for sensitive operations
- Apache optimization for production
- Firewall and security header configuration

### Document Processing
- Enhanced financial document analysis
- Improved text extraction from complex PDFs
- OCR support for English and Arabic documents
- Automatic document categorization
- Enhanced metadata extraction and indexing

A Flask-based web application that provides secure document analysis and AI-powered chatbot functionality for different departments within the Oman Central Bank. Each user can only access documents from their assigned department, ensuring data confidentiality and security.

## 🚀 Features

### Core Functionality

#### Department and Security
- **Department-Secure Access**: Users can only view/search documents from their assigned department
- **Authentication**: bcrypt-hashed passwords with session management
- **Department Isolation**: Strict access control based on user department
- **Audit Logging**: Track sensitive operations and document access

#### Document Processing
- **Document Upload**: Support for PDF, DOCX, DOC, and image files (PNG, JPG, JPEG, TIFF)
- **Text Extraction**: Advanced OCR with English and Arabic support
- **Automatic Categorization**: Content-based department tagging
- **Metadata Analysis**: Enhanced metadata extraction from documents

#### Advanced RAG System
- **Vector Search**: FAISS-based similarity search for relevant document chunks
- **Context-Aware Responses**: Uses document content for accurate answers
- **Intelligent Prioritization**: Multi-layer response system with fallbacks
- **Real-time Indexing**: New documents immediately available for querying

#### Search and AI
- **Local Search**: TF-IDF + cosine similarity search across documents
- **AI Chatbot**: Gemini API integration with RAG enhancement
- **Fallback System**: Progressive degradation through multiple layers
- **Query Analytics**: Track and analyze search patterns

#### Language Support
- **Bilingual Interface**: Complete English and Arabic support
- **Automatic Translation**: Content translation between languages
- **OCR Language Support**: Text extraction for both scripts
- **Multilingual RAG**: Document processing in both languages

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

### Production Implementation Status

#### Completed Features ✅
- **Security**
  - ✅ bcrypt password hashing with secure salt
  - ✅ Session-based authentication with timeout
  - ✅ Department-based access control
  - ✅ File type validation and sanitization
  - ✅ Secure file upload handling
  - ✅ Apache SSL/HTTPS configuration
  - ✅ Security headers (XSS, CSRF, etc.)
  
- **Monitoring & Logging**
  - ✅ Structured logging system
  - ✅ Health check endpoints
  - ✅ Error tracking and reporting
  - ✅ API request logging
  - ✅ Audit logging for document access
  
- **Infrastructure**
  - ✅ Apache production configuration
  - ✅ Systemd service management
  - ✅ Backup system for files
  - ✅ PostgreSQL database integration
  
#### Planned Enhancements 🚀
- **Security Hardening**
  - [ ] Implement IP-based rate limiting
  - [ ] Add JWTs for API authentication
  - [ ] Enable OAuth/SSO integration
  - [ ] Implement MFA support
  
- **Infrastructure**
  - [ ] Set up container orchestration
  - [ ] Implement CDN for static assets
  - [ ] Configure load balancing
  - [ ] Add real-time metrics monitoring
  
- **Data Management**
  - [ ] Implement distributed file storage
  - [ ] Add automated database backups
  - [ ] Set up data retention policies
  - [ ] Enable cross-region replication
  
- **Performance**
  - [ ] Implement response caching
  - [ ] Add WebSocket support
  - [ ] Optimize static asset delivery
  - [ ] Enable database query caching

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

## 🚀 Production Deployment

### Deployment Architecture

```
Internet → Apache (Port 80/443) → React Frontend
                                → Node.js API (Port 3001) → Flask Backend (Port 5000)
```

### Quick Start Deployment

1. **Linux/Ubuntu:**
```bash
# Run the automated deployment script
sudo chmod +x deploy_apache.sh
sudo ./deploy_apache.sh

# Or use the management script
sudo python3 apache_management.py setup
sudo python3 apache_management.py deploy
```

2. **Windows:**
```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup_apache_windows.ps1
```

### Apache Configuration

1. **Install Apache and Dependencies:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install apache2 nodejs npm python3 python3-pip python3-venv
```

2. **Enable Required Modules:**
```bash
sudo a2enmod rewrite headers deflate expires proxy proxy_http
```

3. **Configure Virtual Host:**
- Create `cbo-chatbot.conf` with provided configuration
- Enable the site and restart Apache

4. **Setup SSL/HTTPS:**
```bash
# Using Let's Encrypt
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d yourdomain.com
```

### Service Management

**Enable and Start Services:**
```bash
sudo systemctl enable cbo-api.service
sudo systemctl enable cbo-flask.service
sudo systemctl start cbo-api.service
sudo systemctl start cbo-flask.service
```

### Monitoring and Maintenance

1. **Check Services:**
```bash
# View service logs
sudo journalctl -u cbo-api.service -f
sudo journalctl -u cbo-flask.service -f
```

2. **Apache Management:**
```bash
sudo systemctl status apache2
sudo apache2ctl configtest
```

3. **Backup System:**
```bash
# Regular backups
DIR="/var/backups/cbo-chatbot/$(date +%Y%m%d)"
mkdir -p $DIR
cp -r /var/www/cbo-chatbot* $DIR/
```

For detailed deployment instructions and troubleshooting, see `APACHE_DEPLOYMENT.md`.

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
