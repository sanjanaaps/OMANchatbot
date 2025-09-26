#!/bin/bash

# Complete Apache Deployment Script for Central Bank of Oman Chatbot
# This script sets up the entire production environment

set -e  # Exit on any error

echo "🚀 Central Bank of Oman Chatbot - Apache Deployment"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/var/www/cbo-chatbot-backend"
APACHE_DOC_ROOT="/var/www/cbo-chatbot"
BACKUP_DIR="/var/backups/cbo-chatbot"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

# Update system packages
print_status "Updating system packages..."
apt update && apt upgrade -y

# Install required packages
print_status "Installing required packages..."
apt install -y apache2 nodejs npm python3 python3-pip python3-venv postgresql postgresql-contrib

# Install Node.js dependencies
print_status "Installing Node.js dependencies..."
cd /var/www/cbo-chatbot-backend
npm install

# Install React dependencies
print_status "Installing React dependencies..."
cd frontend
npm install

# Build React application
print_status "Building React application..."
npm run build

# Create Apache document root
print_status "Setting up Apache document root..."
mkdir -p $APACHE_DOC_ROOT

# Copy build files
print_status "Deploying React build..."
cp -r build/* $APACHE_DOC_ROOT/

# Copy Apache configuration files
print_status "Configuring Apache..."
cp apache/.htaccess $APACHE_DOC_ROOT/
cp apache/cbo-chatbot.conf /etc/apache2/sites-available/

# Enable required Apache modules
print_status "Enabling Apache modules..."
a2enmod rewrite headers deflate expires proxy proxy_http

# Enable the site
print_status "Enabling virtual host..."
a2ensite cbo-chatbot.conf

# Disable default site
a2dissite 000-default.conf

# Set proper permissions
print_status "Setting file permissions..."
chown -R www-data:www-data $APACHE_DOC_ROOT
chmod -R 755 $APACHE_DOC_ROOT

# Setup systemd services
print_status "Setting up systemd services..."
cp apache/cbo-api.service /etc/systemd/system/
cp apache/cbo-flask.service /etc/systemd/system/

# Reload systemd and enable services
systemctl daemon-reload
systemctl enable cbo-api.service
systemctl enable cbo-flask.service

# Test Apache configuration
print_status "Testing Apache configuration..."
if apache2ctl configtest; then
    print_success "Apache configuration is valid!"
else
    print_error "Apache configuration test failed!"
    exit 1
fi

# Start services
print_status "Starting services..."
systemctl start cbo-api.service
systemctl start cbo-flask.service
systemctl restart apache2

# Check service status
print_status "Checking service status..."
echo ""
echo "📊 Service Status:"
echo "=================="

if systemctl is-active --quiet apache2; then
    print_success "Apache2: Running"
else
    print_error "Apache2: Failed"
fi

if systemctl is-active --quiet cbo-api.service; then
    print_success "CBO API: Running"
else
    print_error "CBO API: Failed"
fi

if systemctl is-active --quiet cbo-flask.service; then
    print_success "CBO Flask: Running"
else
    print_error "CBO Flask: Failed"
fi

# Show final information
echo ""
print_success "Deployment completed successfully!"
echo ""
echo "🌐 Application URLs:"
echo "   Frontend: http://localhost"
echo "   API: http://localhost/api"
echo "   Health Check: http://localhost/health"
echo ""
echo "📋 Management Commands:"
echo "   sudo systemctl status apache2        # Check Apache status"
echo "   sudo systemctl status cbo-api        # Check API status"
echo "   sudo systemctl status cbo-flask      # Check Flask status"
echo "   sudo systemctl restart apache2       # Restart Apache"
echo "   sudo systemctl restart cbo-api       # Restart API"
echo "   sudo systemctl restart cbo-flask     # Restart Flask"
echo ""
echo "📝 Log Files:"
echo "   Apache Error: /var/log/apache2/cbo-chatbot_error.log"
echo "   Apache Access: /var/log/apache2/cbo-chatbot_access.log"
echo "   API Service: journalctl -u cbo-api -f"
echo "   Flask Service: journalctl -u cbo-flask -f"
echo ""
echo "🔧 Configuration Files:"
echo "   Apache Config: /etc/apache2/sites-available/cbo-chatbot.conf"
echo "   API Service: /etc/systemd/system/cbo-api.service"
echo "   Flask Service: /etc/systemd/system/cbo-flask.service"
echo ""
echo "⚠️  Next Steps:"
echo "   1. Configure SSL certificates for HTTPS"
echo "   2. Set up proper firewall rules"
echo "   3. Configure database backups"
echo "   4. Set up monitoring and logging"
echo "   5. Update production environment variables"
