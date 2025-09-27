# Apache Setup Guide for CBO Flask Application

This guide will help you set up Apache server to run your Flask application on Windows.

## Prerequisites

1. **Python 3.8+** - Already installed
2. **Apache HTTP Server** - Needs to be installed
3. **Administrator privileges** - Required for Apache setup

## Quick Setup (Recommended)

### Option 1: Automated Setup
```bash
# Run the automated setup script
python setup_apache_windows.py setup
```

### Option 2: Batch File Setup
```bash
# Double-click the batch file or run from command prompt
setup_apache.bat
```

## Manual Setup

### Step 1: Install Apache

#### Option A: Using Chocolatey (Recommended)
```bash
# Install Chocolatey if not already installed
# Then install Apache
choco install apache-httpd -y
```

#### Option B: Manual Installation
1. Download Apache from: https://httpd.apache.org/download.cgi
2. Install Apache HTTP Server
3. Add Apache bin directory to your PATH environment variable

### Step 2: Configure Apache

1. **Copy configuration file:**
   ```bash
   # Copy the configuration to Apache conf directory
   copy apache\cbo-flask.conf "C:\Apache24\conf\cbo-flask.conf"
   ```

2. **Update httpd.conf:**
   - Open `C:\Apache24\conf\httpd.conf`
   - Add this line at the end:
   ```apache
   Include conf/cbo-flask.conf
   ```

3. **Enable required modules:**
   - Uncomment these lines in httpd.conf:
   ```apache
   LoadModule rewrite_module modules/mod_rewrite.so
   LoadModule proxy_module modules/mod_proxy.so
   LoadModule proxy_http_module modules/mod_proxy_http.so
   LoadModule headers_module modules/mod_headers.so
   LoadModule deflate_module modules/mod_deflate.so
   LoadModule expires_module modules/mod_expires.so
   ```

### Step 3: Start Services

#### Start Apache:
```bash
# Method 1: Using service
net start Apache2.4

# Method 2: Using httpd command
httpd -k start
```

#### Start Flask Application:
```bash
python app.py
```

### Step 4: Access Your Application

Open your browser and go to:
- **http://localhost** (Apache proxy)
- **http://localhost:5000** (Direct Flask access)

## Management Commands

### Using the Setup Script
```bash
# Complete setup
python setup_apache_windows.py setup

# Start Apache
python setup_apache_windows.py start

# Stop Apache
python setup_apache_windows.py stop

# Restart Apache
python setup_apache_windows.py restart

# Check status
python setup_apache_windows.py status

# Start Flask app
python setup_apache_windows.py flask
```

### Using the Combined Server Script
```bash
# Start both Apache and Flask
python start_servers.py
```

## Configuration Details

### Apache Virtual Host Configuration
The configuration file `apache/cbo-flask.conf` includes:

- **Proxy Configuration**: Routes all requests to Flask app on port 5000
- **Security Headers**: XSS protection, content type options, etc.
- **Compression**: Gzip compression for better performance
- **Caching**: Static asset caching for improved load times
- **Logging**: Error and access logs

### Flask Application Configuration
Make sure your Flask app is configured to:
- Run on `127.0.0.1:5000`
- Handle all routes properly
- Serve static files correctly

## Troubleshooting

### Common Issues

1. **Apache won't start:**
   - Check if port 80 is already in use
   - Verify Apache configuration syntax
   - Check Windows Firewall settings

2. **Flask app not accessible through Apache:**
   - Ensure Flask is running on port 5000
   - Check Apache proxy configuration
   - Verify mod_proxy modules are enabled

3. **Permission errors:**
   - Run command prompt as Administrator
   - Check file permissions in Apache directory

### Checking Logs

**Apache Error Log:**
```
C:\Apache24\logs\error.log
```

**Apache Access Log:**
```
C:\Apache24\logs\access.log
```

**Flask Application Logs:**
- Check console output when running `python app.py`

### Testing Configuration

1. **Test Apache configuration:**
   ```bash
   httpd -t
   ```

2. **Test Flask application:**
   ```bash
   python app.py
   ```

3. **Test proxy connection:**
   - Open browser to http://localhost
   - Should show your Flask application

## Production Considerations

### Security
- Enable HTTPS with SSL certificates
- Configure proper firewall rules
- Use environment variables for sensitive data
- Regular security updates

### Performance
- Enable Apache caching
- Use a production WSGI server (like Gunicorn)
- Configure proper logging levels
- Monitor server resources

### Monitoring
- Set up log monitoring
- Configure health checks
- Use process monitoring tools
- Regular backup procedures

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review Apache and Flask logs
3. Verify all prerequisites are met
4. Test each component individually

## File Structure

```
project/
├── apache/
│   ├── cbo-flask.conf          # Apache virtual host config
│   └── .htaccess              # Apache rewrite rules
├── setup_apache_windows.py    # Automated setup script
├── setup_apache.bat          # Batch file setup
├── start_servers.py          # Combined server startup
└── APACHE_SETUP_GUIDE.md     # This guide
```
