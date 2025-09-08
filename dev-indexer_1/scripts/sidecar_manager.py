#!/usr/bin/env python3
"""
Sidecar Management System for ZenGlow Data Sources
Prevents duplicate sidecar creation and provides cleanup utilities.
"""
import json
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

class SidecarManager:
    """Manages sidecar files to prevent duplicates and handle cleanup"""
    
    SIDECAR_SUFFIX = ".meta.json"
    BACKUP_SUFFIX = ".backup"
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.collision_log: List[Dict[str, str]] = []
    
    def get_sidecar_path(self, file_path: Path) -> Path:
        """Get the expected sidecar path for a given file"""
        return file_path.with_suffix(file_path.suffix + self.SIDECAR_SUFFIX)
    
    def sidecar_exists(self, file_path: Path) -> bool:
        """Check if a sidecar file already exists"""
        sidecar_path = self.get_sidecar_path(file_path)
        return sidecar_path.exists()
    
    def get_file_hash(self, file_path: Path) -> str:
        """Generate a hash of the file content for collision detection"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except (OSError, FileNotFoundError):
            return ""
    
    def load_sidecar(self, file_path: Path) -> Optional[Dict]:
        """Load existing sidecar data"""
        sidecar_path = self.get_sidecar_path(file_path)
        if not sidecar_path.exists():
            return None
        
        try:
            with open(sidecar_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  Could not load sidecar {sidecar_path}: {e}")
            return None
    
    def create_sidecar_safe(self, file_path: Path, metadata: Dict, force: bool = False) -> bool:
        """
        Safely create a sidecar file, preventing overwrites unless forced.
        Returns True if created, False if skipped due to existing file.
        """
        sidecar_path = self.get_sidecar_path(file_path)
        
        if sidecar_path.exists() and not force:
            print(f"⚠️  Sidecar already exists, skipping: {sidecar_path}")
            self.collision_log.append({
                "file": str(file_path),
                "sidecar": str(sidecar_path),
                "action": "skipped",
                "timestamp": datetime.now().isoformat()
            })
            return False
        
        # If forcing and backup doesn't exist, create backup
        if sidecar_path.exists() and force:
            backup_path = sidecar_path.with_suffix(sidecar_path.suffix + self.BACKUP_SUFFIX)
            if not backup_path.exists():
                try:
                    backup_path.write_text(sidecar_path.read_text())
                    print(f"📋 Created backup: {backup_path}")
                except OSError as e:
                    print(f"⚠️  Could not create backup: {e}")
        
        # Add metadata about creation
        enhanced_metadata = metadata.copy()
        enhanced_metadata.update({
            "sidecar_created": datetime.now().isoformat(),
            "source_file_hash": self.get_file_hash(file_path),
            "managed_by": "ZenGlow SidecarManager"
        })
        
        try:
            with open(sidecar_path, 'w') as f:
                json.dump(enhanced_metadata, f, indent=2)
            
            action = "overwritten" if sidecar_path.existed() else "created"
            print(f"✅ Sidecar {action}: {sidecar_path}")
            
            self.collision_log.append({
                "file": str(file_path),
                "sidecar": str(sidecar_path),
                "action": action,
                "timestamp": datetime.now().isoformat()
            })
            return True
            
        except OSError as e:
            print(f"❌ Failed to create sidecar {sidecar_path}: {e}")
            return False
    
    def find_duplicate_sidecars(self) -> Dict[str, List[Path]]:
        """Find potential duplicate sidecars based on content hash"""
        sidecars: Dict[str, List[Path]] = {}
        
        for sidecar_path in self.base_path.rglob(f"*{self.SIDECAR_SUFFIX}"):
            try:
                with open(sidecar_path, 'r') as f:
                    content = f.read()
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                    
                if content_hash in sidecars:
                    sidecars[content_hash].append(sidecar_path)
                else:
                    sidecars[content_hash] = [sidecar_path]
            except (OSError, json.JSONDecodeError):
                continue
        
        # Return only groups with duplicates
        return {h: paths for h, paths in sidecars.items() if len(paths) > 1}
    
    def find_orphaned_sidecars(self) -> List[Path]:
        """Find sidecar files without corresponding source files"""
        orphaned = []
        
        for sidecar_path in self.base_path.rglob(f"*{self.SIDECAR_SUFFIX}"):
            # Reconstruct the original file path
            original_suffix = sidecar_path.suffix.replace(self.SIDECAR_SUFFIX, "")
            source_path = sidecar_path.with_suffix(original_suffix)
            
            if not source_path.exists():
                orphaned.append(sidecar_path)
        
        return orphaned
    
    def cleanup_orphaned_sidecars(self, dry_run: bool = True) -> List[Path]:
        """Remove orphaned sidecar files"""
        orphaned = self.find_orphaned_sidecars()
        removed = []
        
        for sidecar_path in orphaned:
            if dry_run:
                print(f"🔍 Would remove orphaned sidecar: {sidecar_path}")
            else:
                try:
                    sidecar_path.unlink()
                    removed.append(sidecar_path)
                    print(f"🗑️  Removed orphaned sidecar: {sidecar_path}")
                except OSError as e:
                    print(f"⚠️  Could not remove {sidecar_path}: {e}")
        
        return removed
    
    def cleanup_duplicate_sidecars(self, dry_run: bool = True) -> List[Path]:
        """Remove duplicate sidecar files, keeping the first one found"""
        duplicates = self.find_duplicate_sidecars()
        removed = []
        
        for content_hash, paths in duplicates.items():
            print(f"\n📄 Found {len(paths)} duplicate sidecars (hash: {content_hash[:8]}...):")
            for path in paths:
                print(f"   {path}")
            
            # Keep the first one, remove the rest
            to_remove = paths[1:]
            for sidecar_path in to_remove:
                if dry_run:
                    print(f"🔍 Would remove duplicate: {sidecar_path}")
                else:
                    try:
                        sidecar_path.unlink()
                        removed.append(sidecar_path)
                        print(f"🗑️  Removed duplicate: {sidecar_path}")
                    except OSError as e:
                        print(f"⚠️  Could not remove {sidecar_path}: {e}")
        
        return removed
    
    def generate_report(self) -> Dict:
        """Generate a comprehensive sidecar management report"""
        all_sidecars = list(self.base_path.rglob(f"*{self.SIDECAR_SUFFIX}"))
        orphaned = self.find_orphaned_sidecars()
        duplicates = self.find_duplicate_sidecars()
        
        return {
            "total_sidecars": len(all_sidecars),
            "orphaned_count": len(orphaned),
            "duplicate_groups": len(duplicates),
            "total_duplicates": sum(len(paths) - 1 for paths in duplicates.values()),
            "collision_log": self.collision_log,
            "scan_timestamp": datetime.now().isoformat()
        }

def main():
    """CLI interface for sidecar management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ZenGlow Sidecar Management')
    parser.add_argument('--base-path', default='data_sources', help='Base path to scan')
    parser.add_argument('--cleanup-orphaned', action='store_true', help='Remove orphaned sidecars')
    parser.add_argument('--cleanup-duplicates', action='store_true', help='Remove duplicate sidecars')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--report', action='store_true', help='Generate management report')
    
    args = parser.parse_args()
    
    manager = SidecarManager(Path(args.base_path))
    
    if args.cleanup_orphaned:
        print("🔍 Scanning for orphaned sidecars...")
        removed = manager.cleanup_orphaned_sidecars(dry_run=args.dry_run)
        if not args.dry_run:
            print(f"✅ Removed {len(removed)} orphaned sidecars")
    
    if args.cleanup_duplicates:
        print("🔍 Scanning for duplicate sidecars...")
        removed = manager.cleanup_duplicate_sidecars(dry_run=args.dry_run)
        if not args.dry_run:
            print(f"✅ Removed {len(removed)} duplicate sidecars")
    
    if args.report:
        print("\n📊 Sidecar Management Report:")
        report = manager.generate_report()
        print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
