# PowerShell script to setup Apache on Windows for Central Bank of Oman Chatbot
# This script configures Apache to serve the React frontend and proxy API requests

param(
    [string]$ApachePath = "C:\Apache24",
    [string]$DocumentRoot = "C:\Apache24\htdocs\cbo-chatbot",
    [int]$Port = 80
)

Write-Host "🚀 Central Bank of Oman Chatbot - Apache Setup for Windows" -ForegroundColor Blue
Write-Host "=========================================================" -ForegroundColor Blue

# Function to write colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

# Check if Apache is installed
if (-not (Test-Path $ApachePath)) {
    Write-Error "Apache not found at $ApachePath"
    Write-Host "Please install Apache from: https://httpd.apache.org/download.cgi" -ForegroundColor Yellow
    Write-Host "Or use XAMPP: https://www.apachefriends.org/download.html" -ForegroundColor Yellow
    exit 1
}

Write-Status "Apache found at: $ApachePath"

# Create document root directory
Write-Status "Creating document root directory..."
New-Item -ItemType Directory -Force -Path $DocumentRoot | Out-Null

# Build React application
Write-Status "Building React application..."
if (-not (Test-Path "frontend")) {
    Write-Error "Frontend directory not found!"
    exit 1
}

Set-Location frontend
npm install
npm run build
Set-Location ..

if (-not (Test-Path "frontend\build")) {
    Write-Error "React build failed!"
    exit 1
}

# Copy build files to Apache document root
Write-Status "Copying React build to Apache document root..."
Copy-Item -Path "frontend\build\*" -Destination $DocumentRoot -Recurse -Force

# Create .htaccess file for React Router
Write-Status "Creating .htaccess file..."
$htaccessContent = @"
RewriteEngine On
RewriteBase /

# Handle React Router - serve index.html for all routes
RewriteRule ^index\.html$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.html [L]

# Security headers
<IfModule mod_headers.c>
    Header always set X-Content-Type-Options nosniff
    Header always set X-Frame-Options DENY
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
</IfModule>

# Compression
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/plain
    AddOutputFilterByType DEFLATE text/html
    AddOutputFilterByType DEFLATE text/xml
    AddOutputFilterByType DEFLATE text/css
    AddOutputFilterByType DEFLATE application/xml
    AddOutputFilterByType DEFLATE application/xhtml+xml
    AddOutputFilterByType DEFLATE application/rss+xml
    AddOutputFilterByType DEFLATE application/javascript
    AddOutputFilterByType DEFLATE application/x-javascript
</IfModule>
"@

$htaccessContent | Out-File -FilePath "$DocumentRoot\.htaccess" -Encoding UTF8

# Create Apache virtual host configuration
Write-Status "Creating Apache virtual host configuration..."
$vhostConfig = @"
# Central Bank of Oman Chatbot Virtual Host
<VirtualHost *:$Port>
    ServerName localhost
    DocumentRoot "$DocumentRoot"
    
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
    <Directory "$DocumentRoot">
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
        
        # Handle React Router - serve index.html for all routes
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
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    
    # Compression
    <Location />
        SetOutputFilter DEFLATE
        SetEnvIfNoCase Request_URI \.(?:gif|jpe?g|png)$ no-gzip dont-vary
        SetEnvIfNoCase Request_URI \.(?:exe|t?gz|zip|bz2|sit|rar)$ no-gzip dont-vary
    </Location>
    
    # Caching for static assets
    <LocationMatch "\.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$">
        ExpiresActive On
        ExpiresDefault "access plus 1 month"
        Header append Cache-Control "public"
    </LocationMatch>
    
    # Logging
    ErrorLog logs/cbo-chatbot_error.log
    CustomLog logs/cbo-chatbot_access.log combined
    LogLevel info
</VirtualHost>
"@

$vhostConfig | Out-File -FilePath "$ApachePath\conf\extra\cbo-chatbot.conf" -Encoding UTF8

# Update main Apache configuration
Write-Status "Updating Apache main configuration..."
$httpdConfPath = "$ApachePath\conf\httpd.conf"

# Read current configuration
$httpdConf = Get-Content $httpdConfPath

# Check if our virtual host is already included
$includeLine = "Include conf/extra/cbo-chatbot.conf"
if ($httpdConf -notcontains $includeLine) {
    Write-Status "Adding virtual host include to main configuration..."
    Add-Content -Path $httpdConfPath -Value ""
    Add-Content -Path $httpdConfPath -Value "# Central Bank of Oman Chatbot"
    Add-Content -Path $httpdConfPath -Value $includeLine
}

# Enable required modules
Write-Status "Enabling required Apache modules..."
$modulesToEnable = @("rewrite_module", "headers_module", "deflate_module", "expires_module", "proxy_module", "proxy_http_module")

foreach ($module in $modulesToEnable) {
    $moduleLine = "LoadModule $module"
    if ($httpdConf -notcontains $moduleLine) {
        Write-Warning "Module $module not found in configuration. Please enable it manually."
    }
}

# Create startup scripts
Write-Status "Creating startup scripts..."

# Create batch file to start all services
$startScript = @"
@echo off
echo Starting Central Bank of Oman Chatbot Services...

echo Starting Flask Backend...
start "Flask Backend" cmd /k "python run_app.py"

timeout /t 3 /nobreak > nul

echo Starting Node.js API Server...
start "Node.js API" cmd /k "node server.js"

timeout /t 3 /nobreak > nul

echo Starting Apache...
net start Apache2.4

echo All services started!
echo Frontend: http://localhost
echo API: http://localhost/api
pause
"@

$startScript | Out-File -FilePath "start_apache_services.bat" -Encoding ASCII

# Create batch file to stop all services
$stopScript = @"
@echo off
echo Stopping Central Bank of Oman Chatbot Services...

echo Stopping Apache...
net stop Apache2.4

echo Stopping Node.js and Flask processes...
taskkill /f /im node.exe 2>nul
taskkill /f /im python.exe 2>nul

echo All services stopped!
pause
"@

$stopScript | Out-File -FilePath "stop_apache_services.bat" -Encoding ASCII

Write-Success "Apache setup completed successfully!"
Write-Host ""
Write-Host "🌐 Application URLs:" -ForegroundColor Green
Write-Host "   Frontend: http://localhost" -ForegroundColor White
Write-Host "   API: http://localhost/api" -ForegroundColor White
Write-Host "   Health Check: http://localhost/health" -ForegroundColor White
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Yellow
Write-Host "   1. Start Apache service: net start Apache2.4" -ForegroundColor White
Write-Host "   2. Or use the provided batch files:" -ForegroundColor White
Write-Host "      - start_apache_services.bat (starts all services)" -ForegroundColor White
Write-Host "      - stop_apache_services.bat (stops all services)" -ForegroundColor White
Write-Host "   3. Ensure Flask backend is running on port 5000" -ForegroundColor White
Write-Host "   4. Ensure Node.js API server is running on port 3001" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Configuration Files:" -ForegroundColor Yellow
Write-Host "   Apache Config: $ApachePath\conf\extra\cbo-chatbot.conf" -ForegroundColor White
Write-Host "   Document Root: $DocumentRoot" -ForegroundColor White
Write-Host "   .htaccess: $DocumentRoot\.htaccess" -ForegroundColor White
Write-Host ""
Write-Host "📝 Log Files:" -ForegroundColor Yellow
Write-Host "   Apache Error: $ApachePath\logs\cbo-chatbot_error.log" -ForegroundColor White
Write-Host "   Apache Access: $ApachePath\logs\cbo-chatbot_access.log" -ForegroundColor White
