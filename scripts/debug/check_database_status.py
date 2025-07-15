#!/usr/bin/env python3
"""
Database Status Checker (Non-Interactive)

Quick diagnostic script to check Messages database corruption status.
"""

import os
import sys
import sqlite3
import subprocess
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.utils.logger_config import get_logger

logger = get_logger(__name__)


def check_messages_app_running():
    """Check if Messages.app is currently running"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "Messages.app"], 
            capture_output=True, 
            text=True
        )
        return result.returncode == 0
    except:
        return False


def get_database_info(db_path: Path) -> dict:
    """Get information about a database file"""
    info = {
        "exists": db_path.exists(),
        "size": 0,
        "readable": False,
        "corrupted": False,
        "wal_exists": False,
        "shm_exists": False,
        "error": None
    }
    
    if not db_path.exists():
        return info
    
    try:
        info["size"] = db_path.stat().st_size
        
        # Check for WAL and SHM files
        wal_path = db_path.with_suffix(db_path.suffix + "-wal")
        shm_path = db_path.with_suffix(db_path.suffix + "-shm")
        info["wal_exists"] = wal_path.exists()
        info["shm_exists"] = shm_path.exists()
        
        if info["wal_exists"]:
            info["wal_size"] = wal_path.stat().st_size
        if info["shm_exists"]:
            info["shm_size"] = shm_path.stat().st_size
        
        # Try to read the database
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            
            # Quick integrity check
            cursor.execute("PRAGMA integrity_check(1)")
            result = cursor.fetchone()
            
            if result and result[0] == "ok":
                info["readable"] = True
                
                # Get additional info if readable
                cursor.execute("SELECT COUNT(*) FROM message")
                info["message_count"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT MAX(ROWID) FROM message")
                max_rowid = cursor.fetchone()[0]
                info["max_rowid"] = max_rowid if max_rowid else 0
                
            else:
                info["corrupted"] = True
                info["error"] = result[0] if result else "Unknown integrity issue"
                
    except sqlite3.DatabaseError as e:
        info["corrupted"] = True
        info["error"] = str(e)
    except Exception as e:
        info["error"] = str(e)
    
    return info


def main():
    """Main status check function"""
    print("📊 Messages Database Status Check")
    print("=" * 50)
    
    # Check if Messages.app is running
    messages_running = check_messages_app_running()
    print(f"Messages.app running: {'Yes' if messages_running else 'No'}")
    
    if messages_running:
        print("⚠️  Messages.app is running - this can cause access conflicts")
    
    print()
    
    # Define database paths
    source_db = Path.home() / "Library" / "Messages" / "chat.db"
    local_db = Path("./data/messages.db")
    
    # Check source database
    print("1. SOURCE DATABASE (Apple Messages)")
    print("-" * 40)
    print(f"Path: {source_db}")
    
    source_info = get_database_info(source_db)
    
    if not source_info["exists"]:
        print("❌ Source database not found!")
        return 1
    
    print(f"Size: {source_info['size']:,} bytes ({source_info['size']/1024/1024:.1f} MB)")
    print(f"WAL file: {'Yes' if source_info['wal_exists'] else 'No'}", end="")
    if source_info.get("wal_size"):
        print(f" ({source_info['wal_size']:,} bytes)")
    else:
        print()
        
    print(f"SHM file: {'Yes' if source_info['shm_exists'] else 'No'}", end="")
    if source_info.get("shm_size"):
        print(f" ({source_info['shm_size']:,} bytes)")
    else:
        print()
    
    if source_info["corrupted"]:
        print(f"❌ CORRUPTED: {source_info['error']}")
        print("🔧 SOLUTION: Restart Messages.app or reboot your Mac")
    elif source_info["readable"]:
        print("✅ Database is healthy and readable")
        print(f"   Messages: {source_info.get('message_count', 'Unknown'):,}")
        print(f"   Max ROWID: {source_info.get('max_rowid', 'Unknown'):,}")
    else:
        print(f"⚠️  Cannot read database: {source_info.get('error', 'Unknown error')}")
    
    print()
    
    # Check local database
    print("2. LOCAL DATABASE (Our Copy)")
    print("-" * 30)
    print(f"Path: {local_db}")
    
    if local_db.exists():
        local_info = get_database_info(local_db)
        print(f"Size: {local_info['size']:,} bytes ({local_info['size']/1024:.1f} KB)")
        
        if local_info["corrupted"]:
            print(f"❌ CORRUPTED: {local_info['error']}")
            print("🔧 SOLUTION: Delete local database and reinitialize")
            print("   rm ./data/messages.db")
            print("   python scripts/run_polling_service.py poll")
        elif local_info["readable"]:
            print("✅ Local database is healthy")
            if local_info.get('message_count'):
                print(f"   Messages: {local_info['message_count']:,}")
        else:
            print(f"⚠️  Cannot read: {local_info.get('error', 'Unknown')}")
    else:
        print("ℹ️  Local database doesn't exist (normal for first run)")
    
    print()
    
    # Recommendations
    print("🔧 RECOMMENDATIONS")
    print("-" * 20)
    
    if source_info["corrupted"]:
        print("❌ CRITICAL: Source database is corrupted!")
        print("   1. Quit Messages.app completely")
        print("   2. Restart your Mac")
        print("   3. If still corrupted, restore from Time Machine")
        print("   4. DO NOT run polling until fixed")
    elif messages_running:
        print("⚠️  Messages.app is running:")
        print("   • Use slower polling intervals (--interval 5+)")
        print("   • Avoid ultra-fast polling")
        print("   • Consider quitting Messages.app for fastest polling")
    else:
        print("✅ Ready for polling:")
        print("   • Source database is healthy")
        print("   • Messages.app is not running")
        print("   • Safe to use fast polling intervals")
    
    # Return appropriate exit code
    if source_info["corrupted"]:
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())