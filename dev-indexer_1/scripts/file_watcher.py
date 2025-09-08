#!/usr/bin/env python3
"""
ZenGlow File Watcher with Auto-Start venv Integration
Monitors data source folders and triggers ingestion pipeline automatically.
"""
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

class ZenGlowDataHandler(FileSystemEventHandler):
    """File system event handler for ZenGlow data sources"""
    
    def __init__(self, base_path: Path, venv_path: Path, config_path: Path):
        self.base_path = Path(base_path)
        self.venv_path = Path(venv_path)
        self.config_path = Path(config_path)
        self.processing_queue: List[Path] = []
        self.last_processed: Dict[str, float] = {}
        self.debounce_seconds = 2  # Wait 2 seconds before processing
        
        # Supported file extensions for processing
        self.supported_extensions = {'.txt', '.md', '.json', '.csv', '.py', '.tsx', '.jsx'}
        self.sidecar_suffix = '.meta.json'
        
        print(f"📁 Monitoring: {self.base_path}")
        print(f"🐍 Virtual env: {self.venv_path}")
        print(f"⚙️  Config: {self.config_path}")
    
    def should_process_file(self, file_path: Path) -> bool:
        """Determine if a file should trigger processing"""
        # Skip hidden files
        if file_path.name.startswith('.'):
            return False
        
        # Skip sidecar files - they don't trigger processing
        if file_path.name.endswith(self.sidecar_suffix):
            return False
        
        # Only process supported file extensions
        if file_path.suffix not in self.supported_extensions:
            return False
        
        # Check debounce - avoid rapid fire processing
        file_key = str(file_path)
        current_time = time.time()
        if file_key in self.last_processed:
            if current_time - self.last_processed[file_key] < self.debounce_seconds:
                return False
        
        self.last_processed[file_key] = current_time
        return True
    
    def get_python_executable(self) -> Path:
        """Get the Python executable from the virtual environment"""
        if sys.platform == "win32":
            return self.venv_path / "Scripts" / "python.exe"
        else:
            return self.venv_path / "bin" / "python"
    
    def get_data_source_category(self, file_path: Path) -> Optional[str]:
        """Determine the data source category from file path"""
        try:
            # Get relative path from base data sources directory
            rel_path = file_path.relative_to(self.base_path)
            path_parts = rel_path.parts
            
            # Map directory structure to categories
            category_mapping = {
                'wearables': 'physiological_data',
                'ai_pet_feedback': 'behavioral_feedback', 
                'parent_dashboard': 'parental_insights',
                'child_app_input': 'child_self_report',
                'environmental': 'environmental_context',
                'development': 'development_knowledge',
                'operational': 'operational_knowledge',
                'professional_reference': 'professional_knowledge'
            }
            
            # Find the category based on the first directory component
            if path_parts and path_parts[0] in category_mapping:
                return category_mapping[path_parts[0]]
            
            return 'general'
            
        except ValueError:
            # File is not under base_path
            return None
    
    def trigger_ingestion(self, file_path: Path) -> bool:
        """Trigger the ingestion pipeline for a new/modified file"""
        category = self.get_data_source_category(file_path)
        if not category:
            print(f"⚠️  File outside monitored area, skipping: {file_path}")
            return False
        
        python_exe = self.get_python_executable()
        if not python_exe.exists():
            print(f"❌ Python executable not found: {python_exe}")
            return False
        
        # Determine if processing single file or parent directory
        if file_path.is_file():
            source_path = file_path.parent
        else:
            source_path = file_path
        
        # Build the ingestion command
        ingestion_script = self.base_path.parent / "scripts" / "enhanced_intake_to_redis.py"
        cmd = [
            str(python_exe),
            str(ingestion_script),
            "--source", str(source_path),
            "--config", str(self.config_path)
        ]
        
        try:
            print(f"🚀 Triggering ingestion for: {file_path}")
            print(f"📂 Source directory: {source_path}")
            print(f"🏷️  Category: {category}")
            
            # Run the ingestion process
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print(f"✅ Ingestion completed successfully")
                print(f"📊 Output: {result.stdout.strip()}")
                return True
            else:
                print(f"❌ Ingestion failed with code {result.returncode}")
                print(f"📝 Error: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Ingestion timed out after 5 minutes")
            return False
        except Exception as e:
            print(f"💥 Ingestion error: {e}")
            return False
    
    def on_created(self, event):
        """Handle file/directory creation events"""
        if isinstance(event, FileCreatedEvent):
            file_path = Path(event.src_path)
            if self.should_process_file(file_path):
                print(f"📄 New file detected: {file_path.name}")
                self.trigger_ingestion(file_path)
    
    def on_modified(self, event):
        """Handle file modification events"""
        if isinstance(event, FileModifiedEvent):
            file_path = Path(event.src_path)
            if self.should_process_file(file_path):
                print(f"📝 File modified: {file_path.name}")
                self.trigger_ingestion(file_path)

class ZenGlowWatcher:
    """Main watcher class that coordinates file monitoring"""
    
    def __init__(self, base_path: str, venv_path: str, config_path: str):
        self.base_path = Path(base_path)
        self.venv_path = Path(venv_path)
        self.config_path = Path(config_path)
        self.observer = Observer()
        self.handler = ZenGlowDataHandler(self.base_path, self.venv_path, self.config_path)
        
        # Validate paths
        if not self.base_path.exists():
            raise FileNotFoundError(f"Base path does not exist: {self.base_path}")
        if not self.venv_path.exists():
            raise FileNotFoundError(f"Virtual environment not found: {self.venv_path}")
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
    
    def start(self, recursive: bool = True):
        """Start watching the data source directories"""
        print(f"🔍 Starting ZenGlow file watcher...")
        print(f"📁 Watching: {self.base_path}")
        print(f"🔄 Recursive: {recursive}")
        
        # Schedule the observer
        self.observer.schedule(
            self.handler,
            str(self.base_path),
            recursive=recursive
        )
        
        self.observer.start()
        print(f"✅ File watcher started successfully")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n🛑 Stopping file watcher...")
            self.stop()
    
    def stop(self):
        """Stop the file watcher"""
        self.observer.stop()
        self.observer.join()
        print(f"✅ File watcher stopped")

def create_watcher_service(base_path: str, venv_path: str, config_path: str) -> str:
    """Create a systemd service file for the watcher"""
    service_content = f"""[Unit]
Description=ZenGlow Data Ingestion File Watcher
After=network.target redis.service postgresql.service

[Service]
Type=simple
User={os.getenv('USER', 'zenglow')}
WorkingDirectory={Path(base_path).parent}
ExecStart={venv_path}/bin/python {Path(__file__).absolute()} --base-path {base_path} --venv-path {venv_path} --config {config_path}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
    
    service_file = "/etc/systemd/system/zenglow-watcher.service"
    return service_content

def main():
    """CLI interface for the file watcher"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ZenGlow File Watcher with Auto-Start')
    parser.add_argument('--base-path', default='data_sources', help='Base path to monitor')
    parser.add_argument('--venv-path', default='.venv', help='Virtual environment path')
    parser.add_argument('--config', default='data_sources/data_source_config.yaml', help='Configuration file')
    parser.add_argument('--create-service', action='store_true', help='Generate systemd service file')
    parser.add_argument('--no-recursive', action='store_true', help='Disable recursive monitoring')
    
    args = parser.parse_args()
    
    if args.create_service:
        service_content = create_watcher_service(args.base_path, args.venv_path, args.config)
        print("📋 Systemd service file content:")
        print(service_content)
        print("\n💡 To install:")
        print("sudo nano /etc/systemd/system/zenglow-watcher.service")
        print("sudo systemctl daemon-reload")
        print("sudo systemctl enable zenglow-watcher.service")
        print("sudo systemctl start zenglow-watcher.service")
        return
    
    try:
        watcher = ZenGlowWatcher(args.base_path, args.venv_path, args.config)
        watcher.start(recursive=not args.no_recursive)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
