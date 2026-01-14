import os
import time
from datetime import datetime, timedelta
from pathlib import Path
import threading

class FileCleanupService:
    """Auto-delete temporary files after specified days using built-in libraries"""
    
    def __init__(self, temp_dir: str = "./temp_files", max_age_days: int = 2):
        self.temp_dir = Path(temp_dir)
        self.max_age_days = max_age_days
        self.temp_dir.mkdir(exist_ok=True)
        self.running = True
        
        print(f"🗑️ File Cleanup Service initialized")
        print(f"   Temp directory: {self.temp_dir.absolute()}")
        print(f"   Max age: {max_age_days} days")
        print(f"   Cleanup runs every 6 hours")
        
        # Start cleanup scheduler in background
        self._start_scheduler()
    
    def _start_scheduler(self):
        """Run cleanup every 6 hours using threading.Timer"""
        
        def run_cleanup_loop():
            """Background thread that runs cleanup periodically"""
            while self.running:
                try:
                    self.cleanup_old_files()
                except Exception as e:
                    print(f"   ⚠️ Cleanup error: {e}")
                
                # Wait 6 hours (21600 seconds)
                time.sleep(21600)
        
        # Start background thread
        cleanup_thread = threading.Thread(target=run_cleanup_loop, daemon=True)
        cleanup_thread.start()
        
        print(f"   ✅ Cleanup scheduler started (background thread)")
    
    def cleanup_old_files(self):
        """Delete files older than max_age_days"""
        
        print(f"\n🗑️ Running scheduled file cleanup...")
        print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        cutoff_time = datetime.now() - timedelta(days=self.max_age_days)
        deleted_count = 0
        freed_space = 0
        
        try:
            # Check if temp directory exists
            if not self.temp_dir.exists():
                print(f"   ℹ️ Temp directory doesn't exist yet")
                return
            
            # Scan all files
            for file_path in self.temp_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        file_age = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        if file_age < cutoff_time:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_count += 1
                            freed_space += file_size
                            
                            days_old = (datetime.now() - file_age).days
                            print(f"   🗑️ Deleted: {file_path.name} ({days_old} days old)")
                    
                    except Exception as e:
                        print(f"   ⚠️ Failed to delete {file_path.name}: {e}")
            
            # Summary
            if deleted_count > 0:
                print(f"\n   ✅ Cleanup complete:")
                print(f"      Files deleted: {deleted_count}")
                print(f"      Space freed: {freed_space / (1024*1024):.2f} MB")
            else:
                print(f"   ℹ️ No files older than {self.max_age_days} days found")
        
        except Exception as e:
            print(f"   ❌ Cleanup error: {e}")
    
    def save_temp_file(self, data: bytes, filename: str, subfolder: str = "") -> str:
        """
        Save temporary file that will be auto-deleted after max_age_days
        
        Args:
            data: File content (bytes)
            filename: File name
            subfolder: Optional subfolder (e.g., "sunglasses", "watch")
        
        Returns:
            Full path to saved file
        """
        
        # Create subfolder if needed
        if subfolder:
            save_dir = self.temp_dir / subfolder
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = self.temp_dir
        
        file_path = save_dir / filename
        
        try:
            with open(file_path, 'wb') as f:
                f.write(data)
            
            print(f"   💾 Saved temp file: {file_path.name}")
            print(f"      Will be deleted after {self.max_age_days} days")
            
            return str(file_path)
        
        except Exception as e:
            print(f"   ❌ Failed to save temp file: {e}")
            raise
    
    def stop(self):
        """Stop the cleanup service"""
        self.running = False
        print("🗑️ Cleanup service stopped")


# Singleton instance
file_cleanup_service = FileCleanupService()
