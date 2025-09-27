#!/usr/bin/env python3
"""
Apache Setup Script for Windows
Sets up Apache server to run the Flask application
"""

import subprocess
import sys
import os
import time
import shutil
from pathlib import Path

class WindowsApacheManager:
    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.apache_config = self.project_root / "apache" / "cbo-flask.conf"
        self.htaccess_file = self.project_root / "apache" / ".htaccess"
        
    def run_command(self, command, shell=True):
        """Run a shell command and return the result"""
        try:
            result = subprocess.run(command, shell=shell, capture_output=True, text=True, check=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
    
    def check_apache_installed(self):
        """Check if Apache is installed"""
        success, output = self.run_command("httpd -v")
        if success:
            print("✅ Apache is installed")
            return True
        else:
            print("❌ Apache is not installed or not in PATH")
            return False
    
    def check_apache_running(self):
        """Check if Apache is running"""
        success, output = self.run_command("tasklist | findstr httpd")
        if success and "httpd.exe" in output:
            print("✅ Apache is running")
            return True
        else:
            print("❌ Apache is not running")
            return False
    
    def start_apache(self):
        """Start Apache service"""
        print("🚀 Starting Apache...")
        
        # Try to start Apache service
        success, output = self.run_command("net start Apache2.4")
        if success:
            print("✅ Apache started successfully!")
            return True
        else:
            # Try alternative method
            print("Trying alternative start method...")
            success, output = self.run_command("httpd -k start")
            if success:
                print("✅ Apache started successfully!")
                return True
            else:
                print(f"❌ Failed to start Apache: {output}")
                return False
    
    def stop_apache(self):
        """Stop Apache service"""
        print("🛑 Stopping Apache...")
        
        # Try to stop Apache service
        success, output = self.run_command("net stop Apache2.4")
        if success:
            print("✅ Apache stopped successfully!")
            return True
        else:
            # Try alternative method
            print("Trying alternative stop method...")
            success, output = self.run_command("httpd -k stop")
            if success:
                print("✅ Apache stopped successfully!")
                return True
            else:
                print(f"❌ Failed to stop Apache: {output}")
                return False
    
    def restart_apache(self):
        """Restart Apache service"""
        print("🔄 Restarting Apache...")
        self.stop_apache()
        time.sleep(2)
        return self.start_apache()
    
    def install_apache(self):
        """Install Apache using Chocolatey or provide instructions"""
        print("📦 Installing Apache...")
        
        # Check if Chocolatey is available
        success, output = self.run_command("choco --version")
        if success:
            print("Using Chocolatey to install Apache...")
            success, output = self.run_command("choco install apache-httpd -y")
            if success:
                print("✅ Apache installed successfully!")
                return True
            else:
                print(f"❌ Failed to install Apache: {output}")
                return False
        else:
            print("❌ Chocolatey not found. Please install Apache manually:")
            print("1. Download Apache from: https://httpd.apache.org/download.cgi")
            print("2. Install Apache HTTP Server")
            print("3. Add Apache bin directory to your PATH")
            return False
    
    def setup_configuration(self):
        """Set up Apache configuration"""
        print("⚙️ Setting up Apache configuration...")
        
        # Find Apache installation directory
        apache_dirs = [
            "C:\\Apache24",
            "C:\\Program Files\\Apache Software Foundation\\Apache2.4",
            "C:\\Program Files (x86)\\Apache Software Foundation\\Apache2.4",
            "C:\\xampp\\apache",
            "C:\\wamp64\\bin\\apache\\apache2.4.54"
        ]
        
        apache_dir = None
        for dir_path in apache_dirs:
            if os.path.exists(dir_path):
                apache_dir = dir_path
                break
        
        if not apache_dir:
            print("❌ Apache installation directory not found")
            print("Please specify your Apache installation directory:")
            apache_dir = input("Apache directory: ").strip()
            if not os.path.exists(apache_dir):
                print("❌ Invalid Apache directory")
                return False
        
        print(f"📁 Found Apache at: {apache_dir}")
        
        # Copy configuration file
        conf_dir = Path(apache_dir) / "conf"
        if conf_dir.exists():
            # Copy our configuration
            target_conf = conf_dir / "cbo-flask.conf"
            shutil.copy2(self.apache_config, target_conf)
            print(f"✅ Configuration copied to: {target_conf}")
            
            # Update httpd.conf to include our configuration
            httpd_conf = conf_dir / "httpd.conf"
            if httpd_conf.exists():
                with open(httpd_conf, 'r') as f:
                    content = f.read()
                
                if "cbo-flask.conf" not in content:
                    with open(httpd_conf, 'a') as f:
                        f.write("\n# Include CBO Flask configuration\n")
                        f.write("Include conf/cbo-flask.conf\n")
                    print("✅ Added include directive to httpd.conf")
                else:
                    print("✅ Configuration already included in httpd.conf")
            
            return True
        else:
            print(f"❌ Apache conf directory not found: {conf_dir}")
            return False
    
    def start_flask_app(self):
        """Start the Flask application"""
        print("🐍 Starting Flask application...")
        
        # Change to project directory
        os.chdir(self.project_root)
        
        # Start Flask app
        success, output = self.run_command("python app.py")
        if success:
            print("✅ Flask application started!")
            return True
        else:
            print(f"❌ Failed to start Flask application: {output}")
            return False
    
    def setup_complete(self):
        """Complete setup process"""
        print("🎯 Setting up CBO Flask Application with Apache")
        print("=" * 50)
        
        # Check if Apache is installed
        if not self.check_apache_installed():
            if not self.install_apache():
                return False
        
        # Set up configuration
        if not self.setup_configuration():
            return False
        
        # Start Apache
        if not self.start_apache():
            return False
        
        print("\n" + "=" * 50)
        print("✅ Setup completed successfully!")
        print("🌐 Your application should now be available at:")
        print("   http://localhost")
        print("   http://localhost:80")
        print("\n📝 Next steps:")
        print("1. Start your Flask application: python app.py")
        print("2. Open your browser and go to http://localhost")
        print("3. If you encounter issues, check Apache error logs")
        
        return True

def main():
    manager = WindowsApacheManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "setup":
            manager.setup_complete()
        elif command == "start":
            manager.start_apache()
        elif command == "stop":
            manager.stop_apache()
        elif command == "restart":
            manager.restart_apache()
        elif command == "status":
            manager.check_apache_running()
        elif command == "flask":
            manager.start_flask_app()
        else:
            print("❌ Unknown command. Available commands:")
            print("  setup   - Complete setup process")
            print("  start   - Start Apache")
            print("  stop    - Stop Apache")
            print("  restart - Restart Apache")
            print("  status  - Check Apache status")
            print("  flask   - Start Flask application")
    else:
        print("🎯 CBO Flask Apache Setup")
        print("=" * 30)
        print("Available commands:")
        print("  python setup_apache_windows.py setup   - Complete setup")
        print("  python setup_apache_windows.py start   - Start Apache")
        print("  python setup_apache_windows.py stop    - Stop Apache")
        print("  python setup_apache_windows.py restart - Restart Apache")
        print("  python setup_apache_windows.py status  - Check status")
        print("  python setup_apache_windows.py flask   - Start Flask app")

if __name__ == "__main__":
    main()
