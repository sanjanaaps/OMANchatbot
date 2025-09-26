#!/bin/bash

# Production Build Script for Central Bank of Oman Chatbot
# This script builds the React app and prepares it for Apache deployment

set -e  # Exit on any error

echo "🏗️  Building Central Bank of Oman Chatbot for Production"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APACHE_DOCUMENT_ROOT="/var/www/cbo-chatbot"
BACKUP_DIR="/var/backups/cbo-chatbot"
BUILD_DIR="frontend/build"

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
if [[ $EUID -eq 0 ]]; then
    print_warning "Running as root. This is recommended for Apache deployment."
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    print_error "npm is not installed. Please install npm first."
    exit 1
fi

print_status "Installing Node.js dependencies..."
npm install

print_status "Installing React dependencies..."
cd frontend
npm install

print_status "Building React application for production..."
npm run build

if [ ! -d "$BUILD_DIR" ]; then
    print_error "Build directory not found. Build may have failed."
    exit 1
fi

print_success "React build completed successfully!"

# Create backup if Apache directory exists
if [ -d "$APACHE_DOCUMENT_ROOT" ]; then
    print_status "Creating backup of existing deployment..."
    sudo mkdir -p "$BACKUP_DIR"
    sudo cp -r "$APACHE_DOCUMENT_ROOT" "$BACKUP_DIR/backup-$(date +%Y%m%d-%H%M%S)"
    print_success "Backup created successfully!"
fi

# Create Apache document root if it doesn't exist
print_status "Setting up Apache document root..."
sudo mkdir -p "$APACHE_DOCUMENT_ROOT"

# Copy build files to Apache directory
print_status "Deploying React build to Apache..."
sudo cp -r "$BUILD_DIR"/* "$APACHE_DOCUMENT_ROOT/"

# Copy .htaccess file
print_status "Copying Apache configuration..."
sudo cp "../apache/.htaccess" "$APACHE_DOCUMENT_ROOT/"

# Set proper permissions
print_status "Setting file permissions..."
sudo chown -R www-data:www-data "$APACHE_DOCUMENT_ROOT"
sudo chmod -R 755 "$APACHE_DOCUMENT_ROOT"

# Enable Apache modules if not already enabled
print_status "Enabling required Apache modules..."
sudo a2enmod rewrite
sudo a2enmod headers
sudo a2enmod deflate
sudo a2enmod expires
sudo a2enmod proxy
sudo a2enmod proxy_http

# Copy and enable virtual host
print_status "Configuring Apache virtual host..."
sudo cp "../apache/cbo-chatbot.conf" "/etc/apache2/sites-available/"
sudo a2ensite cbo-chatbot.conf

# Test Apache configuration
print_status "Testing Apache configuration..."
if sudo apache2ctl configtest; then
    print_success "Apache configuration is valid!"
else
    print_error "Apache configuration test failed!"
    exit 1
fi

# Restart Apache
print_status "Restarting Apache..."
sudo systemctl restart apache2

print_success "Production deployment completed successfully!"
echo ""
echo "🌐 Application URLs:"
echo "   Frontend: http://localhost"
echo "   API: http://localhost/api"
echo "   Health Check: http://localhost/health"
echo ""
echo "📋 Next Steps:"
echo "   1. Ensure Flask backend is running on port 5000"
echo "   2. Ensure Node.js API server is running on port 3001"
echo "   3. Test the application at http://localhost"
echo "   4. Check Apache logs: /var/log/apache2/cbo-chatbot_*.log"
echo ""
echo "🔧 Management Commands:"
echo "   sudo systemctl status apache2    # Check Apache status"
echo "   sudo systemctl restart apache2   # Restart Apache"
echo "   sudo tail -f /var/log/apache2/cbo-chatbot_error.log  # View error logs"
echo "   sudo tail -f /var/log/apache2/cbo-chatbot_access.log # View access logs"
