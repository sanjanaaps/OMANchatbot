# Deployment Guide - Oman Central Bank Document Analyzer

## Quick Start

### 1. Prerequisites
- Python 3.8+
- PostgreSQL (local or cloud)
- Google Gemini API key

### 2. Installation
```bash
# Clone and setup
git clone <repository-url>
cd oman-central-bank-doc-analyzer
python -m venv myenv
source myenv/bin/activate  # Windows: myenv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export POSTGRES_URI="postgresql://postgres:1234@localhost:5432/doc_analyzer"
export FLASK_SECRET_KEY="your-secret-key"
export GEMINI_API_KEY="your-gemini-api-key"

# Initialize database
python migrate_to_postgres.py
python seed_users.py

# Start application
python app.py
```

### 3. Test Users
- `finance_user` / `finance123` (Finance)
- `policy_user` / `policy123` (Monetary Policy & Banking)
- `currency_user` / `currency123` (Currency)
- `legal_user` / `legal123` (Legal & Compliance)
- `itfinance_user` / `itfinance123` (IT / Finance)

## Production Deployment

### Environment Variables
```bash
POSTGRES_URI=postgresql://user:pass@host:5432/doc_analyzer
FLASK_SECRET_KEY=strong-random-secret-key
GEMINI_API_KEY=your-gemini-api-key
FLASK_ENV=production
```

### Using Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## Security Checklist

### Required for Production
- [ ] Use HTTPS
- [ ] Set strong FLASK_SECRET_KEY
- [ ] Enable PostgreSQL authentication
- [ ] Use environment variables for secrets
- [ ] Implement rate limiting
- [ ] Add CSRF protection
- [ ] Set up proper logging
- [ ] Configure backup strategy
- [ ] Use secure file storage
- [ ] Implement audit logging

### Optional Enhancements
- [ ] Add user management interface
- [ ] Implement document versioning
- [ ] Add advanced search filters
- [ ] Create API endpoints
- [ ] Add document collaboration features
- [ ] Implement document approval workflow

## Monitoring

### Health Checks
- Database connectivity
- Gemini API availability
- File upload functionality
- Search performance

### Logs
- Application logs: Console output
- Error logs: Check for exceptions
- Access logs: User activity
- Security logs: Authentication events

## Troubleshooting

### Common Issues
1. **PostgreSQL Connection**: Check URI and network
2. **Gemini API**: Verify key and quota
3. **File Uploads**: Check permissions and size limits
4. **Text Extraction**: Install system dependencies

### Support
Contact the IT department for technical support.
