#!/usr/bin/env python3
"""
Apache Management Script for Central Bank of Oman Chatbot
Provides easy management of Apache server and deployment
"""

import subprocess
import sys
import os
import time
import argparse
from pathlib import Path

class ApacheManager:
    def __init__(self):
        self.apache_doc_root = "/var/www/cbo-chatbot"
        self.backup_dir = "/var/backups/cbo-chatbot"
        self.config_file = "apache/cbo-chatbot.conf"
        self.htaccess_file = "apache/.htaccess"
        
    def run_command(self, command, sudo=False):
        """Run a shell command and return the result"""
        try:
            if sudo:
                command = ["sudo"] + command
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
    
    def check_apache_status(self):
        """Check if Apache is running"""
        success, output = self.run_command(["systemctl", "is-active", "apache2"])
        return success and "active" in output
    
    def start_apache(self):
        """Start Apache service"""
        print("🚀 Starting Apache...")
        success, output = self.run_command(["systemctl", "start", "apache2"], sudo=True)
        if success:
            print("✅ Apache started successfully!")
            return True
        else:
            print(f"❌ Failed to start Apache: {output}")
            return False
    
    def stop_apache(self):
        """Stop Apache service"""
        print("🛑 Stopping Apache...")
        success, output = self.run_command(["systemctl", "stop", "apache2"], sudo=True)
        if success:
            print("✅ Apache stopped successfully!")
            return True
        else:
            print(f"❌ Failed to stop Apache: {output}")
            return False
    
    def restart_apache(self):
        """Restart Apache service"""
        print("🔄 Restarting Apache...")
        success, output = self.run_command(["systemctl", "restart", "apache2"], sudo=True)
        if success:
            print("✅ Apache restarted successfully!")
            return True
        else:
            print(f"❌ Failed to restart Apache: {output}")
            return False
    
    def reload_apache(self):
        """Reload Apache configuration"""
        print("🔄 Reloading Apache configuration...")
        success, output = self.run_command(["systemctl", "reload", "apache2"], sudo=True)
        if success:
            print("✅ Apache configuration reloaded successfully!")
            return True
        else:
            print(f"❌ Failed to reload Apache: {output}")
            return False
    
    def test_config(self):
        """Test Apache configuration"""
        print("🧪 Testing Apache configuration...")
        success, output = self.run_command(["apache2ctl", "configtest"], sudo=True)
        if success:
            print("✅ Apache configuration is valid!")
            return True
        else:
            print(f"❌ Apache configuration test failed: {output}")
            return False
    
    def enable_modules(self):
        """Enable required Apache modules"""
        modules = ["rewrite", "headers", "deflate", "expires", "proxy", "proxy_http"]
        print("🔧 Enabling Apache modules...")
        
        for module in modules:
            success, output = self.run_command(["a2enmod", module], sudo=True)
            if success:
                print(f"✅ Module {module} enabled")
            else:
                print(f"⚠️  Module {module} may already be enabled or failed: {output}")
    
    def setup_virtual_host(self):
        """Setup Apache virtual host"""
        print("🌐 Setting up Apache virtual host...")
        
        # Copy configuration file
        if not os.path.exists(self.config_file):
            print(f"❌ Configuration file not found: {self.config_file}")
            return False
        
        success, output = self.run_command([
            "cp", self.config_file, "/etc/apache2/sites-available/"
        ], sudo=True)
        
        if not success:
            print(f"❌ Failed to copy configuration: {output}")
            return False
        
        # Enable site
        success, output = self.run_command(["a2ensite", "cbo-chatbot.conf"], sudo=True)
        if success:
            print("✅ Virtual host enabled successfully!")
            return True
        else:
            print(f"❌ Failed to enable virtual host: {output}")
            return False
    
    def build_and_deploy(self):
        """Build React app and deploy to Apache"""
        print("🏗️  Building and deploying React application...")
        
        # Check if frontend directory exists
        if not os.path.exists("frontend"):
            print("❌ Frontend directory not found!")
            return False
        
        # Install dependencies
        print("📦 Installing Node.js dependencies...")
        success, output = self.run_command(["npm", "install"])
        if not success:
            print(f"❌ Failed to install Node.js dependencies: {output}")
            return False
        
        # Install React dependencies
        print("📦 Installing React dependencies...")
        success, output = self.run_command(["npm", "install"], cwd="frontend")
        if not success:
            print(f"❌ Failed to install React dependencies: {output}")
            return False
        
        # Build React app
        print("🔨 Building React application...")
        success, output = self.run_command(["npm", "run", "build"], cwd="frontend")
        if not success:
            print(f"❌ Failed to build React app: {output}")
            return False
        
        # Create backup if directory exists
        if os.path.exists(self.apache_doc_root):
            print("💾 Creating backup...")
            backup_name = f"backup-{int(time.time())}"
            self.run_command([
                "mkdir", "-p", f"{self.backup_dir}/{backup_name}"
            ], sudo=True)
            self.run_command([
                "cp", "-r", self.apache_doc_root, f"{self.backup_dir}/{backup_name}/"
            ], sudo=True)
        
        # Create document root
        self.run_command(["mkdir", "-p", self.apache_doc_root], sudo=True)
        
        # Copy build files
        print("📁 Copying build files...")
        success, output = self.run_command([
            "cp", "-r", "frontend/build/*", self.apache_doc_root
        ], sudo=True)
        
        # Copy .htaccess
        if os.path.exists(self.htaccess_file):
            self.run_command([
                "cp", self.htaccess_file, self.apache_doc_root
            ], sudo=True)
        
        # Set permissions
        print("🔐 Setting permissions...")
        self.run_command([
            "chown", "-R", "www-data:www-data", self.apache_doc_root
        ], sudo=True)
        self.run_command([
            "chmod", "-R", "755", self.apache_doc_root
        ], sudo=True)
        
        print("✅ Deployment completed successfully!")
        return True
    
    def show_logs(self, log_type="error", lines=50):
        """Show Apache logs"""
        log_files = {
            "error": "/var/log/apache2/cbo-chatbot_error.log",
            "access": "/var/log/apache2/cbo-chatbot_access.log",
            "general": "/var/log/apache2/error.log"
        }
        
        log_file = log_files.get(log_type, log_files["error"])
        print(f"📋 Showing last {lines} lines of {log_type} log:")
        print("-" * 60)
        
        success, output = self.run_command([
            "tail", "-n", str(lines), log_file
        ], sudo=True)
        
        if success:
            print(output)
        else:
            print(f"❌ Failed to read log file: {output}")
    
    def show_status(self):
        """Show comprehensive status"""
        print("📊 Central Bank of Oman Chatbot - Apache Status")
        print("=" * 60)
        
        # Apache status
        if self.check_apache_status():
            print("🟢 Apache: Running")
        else:
            print("🔴 Apache: Stopped")
        
        # Document root
        if os.path.exists(self.apache_doc_root):
            print(f"🟢 Document Root: {self.apache_doc_root} (exists)")
        else:
            print(f"🔴 Document Root: {self.apache_doc_root} (missing)")
        
        # Configuration
        if os.path.exists("/etc/apache2/sites-enabled/cbo-chatbot.conf"):
            print("🟢 Virtual Host: Enabled")
        else:
            print("🔴 Virtual Host: Not enabled")
        
        # Test configuration
        if self.test_config():
            print("🟢 Configuration: Valid")
        else:
            print("🔴 Configuration: Invalid")
        
        print("\n🌐 URLs:")
        print("   Frontend: http://localhost")
        print("   API: http://localhost/api")
        print("   Health: http://localhost/health")

def main():
    parser = argparse.ArgumentParser(description="Apache Management for CBO Chatbot")
    parser.add_argument("action", choices=[
        "start", "stop", "restart", "reload", "status", "test", 
        "deploy", "logs", "setup", "modules"
    ], help="Action to perform")
    parser.add_argument("--log-type", choices=["error", "access", "general"], 
                       default="error", help="Log type for logs action")
    parser.add_argument("--lines", type=int, default=50, 
                       help="Number of log lines to show")
    
    args = parser.parse_args()
    manager = ApacheManager()
    
    if args.action == "start":
        manager.start_apache()
    elif args.action == "stop":
        manager.stop_apache()
    elif args.action == "restart":
        manager.restart_apache()
    elif args.action == "reload":
        manager.reload_apache()
    elif args.action == "status":
        manager.show_status()
    elif args.action == "test":
        manager.test_config()
    elif args.action == "deploy":
        manager.build_and_deploy()
    elif args.action == "logs":
        manager.show_logs(args.log_type, args.lines)
    elif args.action == "setup":
        manager.enable_modules()
        manager.setup_virtual_host()
        manager.test_config()
        manager.restart_apache()
    elif args.action == "modules":
        manager.enable_modules()

if __name__ == "__main__":
    main()
