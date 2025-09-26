# Apache Deployment Guide for Central Bank of Oman Chatbot

## Overview

This guide provides complete instructions for deploying the Central Bank of Oman Chatbot using Apache as the web server. Apache will serve the React frontend and proxy API requests to the Node.js server.

## Architecture

```
Internet → Apache (Port 80/443) → React Frontend
                                → Node.js API (Port 3001) → Flask Backend (Port 5000)
```

## Prerequisites

### Linux/Ubuntu
- Ubuntu 18.04+ or similar Linux distribution
- Root or sudo access
- Node.js 16+ and npm
- Python 3.8+
- PostgreSQL (for database)

### Windows
- Windows 10/11
- Apache 2.4+ (or XAMPP)
- Node.js 16+ and npm
- Python 3.8+
- PostgreSQL (for database)

## Quick Start

### Linux/Ubuntu Deployment

1. **Clone and setup the project:**
```bash
# Copy project files to /var/www/cbo-chatbot-backend
sudo cp -r /path/to/your/project /var/www/cbo-chatbot-backend
cd /var/www/cbo-chatbot-backend
```

2. **Run the automated deployment script:**
```bash
sudo chmod +x deploy_apache.sh
sudo ./deploy_apache.sh
```

3. **Or use the management script:**
```bash
# Setup everything
sudo python3 apache_management.py setup

# Deploy the application
sudo python3 apache_management.py deploy

# Check status
sudo python3 apache_management.py status
```

### Windows Deployment

1. **Install Apache:**
   - Download from: https://httpd.apache.org/download.cgi
   - Or use XAMPP: https://www.apachefriends.org/download.html

2. **Run the PowerShell setup script:**
```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup_apache_windows.ps1
```

3. **Start services:**
```cmd
# Use the provided batch file
start_apache_services.bat
```

## Manual Setup

### 1. Install Apache and Dependencies

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install apache2 nodejs npm python3 python3-pip python3-venv
```

#### CentOS/RHEL:
```bash
sudo yum install httpd nodejs npm python3 python3-pip
```

#### Windows:
- Download Apache from official website
- Install Node.js from nodejs.org
- Install Python from python.org

### 2. Build React Application

```bash
# Install dependencies
npm install
cd frontend
npm install

# Build for production
npm run build
```

### 3. Configure Apache

#### Create Virtual Host Configuration

Create `/etc/apache2/sites-available/cbo-chatbot.conf` (Linux) or `conf/extra/cbo-chatbot.conf` (Windows):

```apache
<VirtualHost *:80>
    ServerName localhost
    DocumentRoot /var/www/cbo-chatbot
    
    # Enable mod_rewrite for React Router
    RewriteEngine On
    
    # Proxy API requests to Node.js server
    ProxyPreserveHost On
    ProxyRequests Off
    
    # API routes - proxy to Node.js server
    ProxyPass /api/ http://localhost:3001/api/
    ProxyPassReverse /api/ http://localhost:3001/api/
    
    # Health check endpoint
    ProxyPass /health http://localhost:3001/health
    ProxyPassReverse /health http://localhost:3001/health
    
    # Serve React static files
    <Directory /var/www/cbo-chatbot>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
        
        # Handle React Router
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\.html$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /index.html [L]
    </Directory>
    
    # Security headers
    Header always set X-Content-Type-Options nosniff
    Header always set X-Frame-Options DENY
    Header always set X-XSS-Protection "1; mode=block"
    
    # Logging
    ErrorLog ${APACHE_LOG_DIR}/cbo-chatbot_error.log
    CustomLog ${APACHE_LOG_DIR}/cbo-chatbot_access.log combined
</VirtualHost>
```

#### Enable Required Modules

```bash
# Linux
sudo a2enmod rewrite headers deflate expires proxy proxy_http

# Windows - Edit httpd.conf and uncomment:
# LoadModule rewrite_module modules/mod_rewrite.so
# LoadModule headers_module modules/mod_headers.so
# LoadModule deflate_module modules/mod_deflate.so
# LoadModule expires_module modules/mod_expires.so
# LoadModule proxy_module modules/mod_proxy.so
# LoadModule proxy_http_module modules/mod_proxy_http.so
```

#### Enable the Site

```bash
# Linux
sudo a2ensite cbo-chatbot.conf
sudo a2dissite 000-default.conf
sudo systemctl restart apache2

# Windows - Add to httpd.conf:
# Include conf/extra/cbo-chatbot.conf
# Then restart Apache service
```

### 4. Deploy React Build

```bash
# Create document root
sudo mkdir -p /var/www/cbo-chatbot

# Copy build files
sudo cp -r frontend/build/* /var/www/cbo-chatbot/

# Copy .htaccess for React Router
sudo cp apache/.htaccess /var/www/cbo-chatbot/

# Set permissions
sudo chown -R www-data:www-data /var/www/cbo-chatbot
sudo chmod -R 755 /var/www/cbo-chatbot
```

### 5. Setup Systemd Services (Linux)

#### Node.js API Service

Create `/etc/systemd/system/cbo-api.service`:

```ini
[Unit]
Description=Central Bank of Oman Chatbot API Server
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/cbo-chatbot-backend
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=10
Environment=NODE_ENV=production
Environment=NODE_PORT=3001

[Install]
WantedBy=multi-user.target
```

#### Flask Backend Service

Create `/etc/systemd/system/cbo-flask.service`:

```ini
[Unit]
Description=Central Bank of Oman Chatbot Flask Backend
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/cbo-chatbot-backend
ExecStart=/usr/bin/python3 run_app.py
Restart=always
RestartSec=10
Environment=FLASK_ENV=production

[Install]
WantedBy=multi-user.target
```

#### Enable and Start Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable cbo-api.service
sudo systemctl enable cbo-flask.service
sudo systemctl start cbo-api.service
sudo systemctl start cbo-flask.service
```

## Management Commands

### Using the Management Script

```bash
# Check status
python3 apache_management.py status

# Start/stop/restart Apache
python3 apache_management.py start
python3 apache_management.py stop
python3 apache_management.py restart

# Deploy new version
python3 apache_management.py deploy

# View logs
python3 apache_management.py logs --log-type error
python3 apache_management.py logs --log-type access

# Test configuration
python3 apache_management.py test
```

### Manual Commands

#### Apache Management
```bash
# Check status
sudo systemctl status apache2

# Start/stop/restart
sudo systemctl start apache2
sudo systemctl stop apache2
sudo systemctl restart apache2

# Test configuration
sudo apache2ctl configtest

# Reload configuration
sudo systemctl reload apache2
```

#### Service Management
```bash
# Check service status
sudo systemctl status cbo-api.service
sudo systemctl status cbo-flask.service

# Start/stop services
sudo systemctl start cbo-api.service
sudo systemctl stop cbo-api.service
sudo systemctl restart cbo-api.service
```

## SSL/HTTPS Setup

### Using Let's Encrypt (Linux)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-apache

# Get certificate
sudo certbot --apache -d yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Manual SSL Setup

1. **Obtain SSL certificates** from your CA
2. **Update virtual host** to include HTTPS configuration
3. **Redirect HTTP to HTTPS** for security

## Monitoring and Logs

### Log Files

#### Apache Logs
- Error Log: `/var/log/apache2/cbo-chatbot_error.log`
- Access Log: `/var/log/apache2/cbo-chatbot_access.log`

#### Service Logs
```bash
# View service logs
sudo journalctl -u cbo-api.service -f
sudo journalctl -u cbo-flask.service -f

# View recent logs
sudo journalctl -u cbo-api.service --since "1 hour ago"
```

### Health Checks

```bash
# Check if services are responding
curl http://localhost/health
curl http://localhost/api/health

# Check Apache status
sudo systemctl is-active apache2
```

## Troubleshooting

### Common Issues

1. **Apache won't start:**
   ```bash
   sudo apache2ctl configtest
   sudo systemctl status apache2
   sudo journalctl -u apache2
   ```

2. **API not responding:**
   ```bash
   sudo systemctl status cbo-api.service
   sudo journalctl -u cbo-api.service
   ```

3. **React Router not working:**
   - Check if `.htaccess` file exists
   - Verify `mod_rewrite` is enabled
   - Check Apache error logs

4. **Permission issues:**
   ```bash
   sudo chown -R www-data:www-data /var/www/cbo-chatbot
   sudo chmod -R 755 /var/www/cbo-chatbot
   ```

### Performance Optimization

1. **Enable compression:**
   ```apache
   LoadModule deflate_module modules/mod_deflate.so
   <Location />
       SetOutputFilter DEFLATE
   </Location>
   ```

2. **Enable caching:**
   ```apache
   <LocationMatch "\.(css|js|png|jpg|jpeg|gif|ico|svg)$">
       ExpiresActive On
       ExpiresDefault "access plus 1 month"
   </LocationMatch>
   ```

3. **Optimize Apache configuration:**
   - Adjust `MaxRequestWorkers`
   - Enable `KeepAlive`
   - Configure `Timeout` values

## Security Considerations

1. **Firewall Configuration:**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw deny 3001/tcp  # Block direct access to Node.js
   sudo ufw deny 5000/tcp  # Block direct access to Flask
   ```

2. **Security Headers:**
   - Already configured in virtual host
   - Consider adding CSP headers

3. **SSL/TLS:**
   - Use strong ciphers
   - Enable HSTS
   - Regular certificate renewal

## Backup and Recovery

### Backup Script

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/cbo-chatbot"
DATE=$(date +%Y%m%d-%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR/$DATE

# Backup application files
cp -r /var/www/cbo-chatbot-backend $BACKUP_DIR/$DATE/
cp -r /var/www/cbo-chatbot $BACKUP_DIR/$DATE/

# Backup Apache configuration
cp /etc/apache2/sites-available/cbo-chatbot.conf $BACKUP_DIR/$DATE/

# Backup systemd services
cp /etc/systemd/system/cbo-*.service $BACKUP_DIR/$DATE/

echo "Backup completed: $BACKUP_DIR/$DATE"
```

### Recovery

```bash
# Restore from backup
sudo cp -r /var/backups/cbo-chatbot/20240101-120000/* /var/www/
sudo systemctl restart apache2
sudo systemctl restart cbo-api.service
sudo systemctl restart cbo-flask.service
```

## Production Checklist

- [ ] SSL certificates installed and configured
- [ ] Firewall rules configured
- [ ] Database backups scheduled
- [ ] Log rotation configured
- [ ] Monitoring and alerting setup
- [ ] Performance optimization applied
- [ ] Security headers configured
- [ ] Error pages customized
- [ ] Health checks implemented
- [ ] Documentation updated
