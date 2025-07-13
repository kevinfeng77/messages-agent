#!/usr/bin/env python3
"""
Copy Messages Database Script

This script creates a safe copy of the macOS Messages database for processing.
It handles WAL/SHM files and performs proper checkpointing.

Usage:
    python scripts/copy_messages_database.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.manager import DatabaseManager
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


def main():
    """Create a safe copy of the Messages database"""
    print("=== Messages Database Copy Script ===\n")
    
    # Initialize database manager with copy subdirectory
    db_manager = DatabaseManager("./data/copy")
    
    print("1. Verifying source Messages database...")
    if not db_manager.verify_source_database():
        print("❌ Failed to verify source Messages database")
        print("   Make sure Messages app has been used and database exists")
        return False
    
    print(f"✅ Source database verified at {db_manager.source_db_path}")
    
    print("\n2. Creating safe database copy...")
    copy_path = db_manager.create_safe_copy()
    
    if not copy_path:
        print("❌ Failed to create database copy")
        return False
    
    print(f"✅ Database copy created at {copy_path}")
    
    print("\n3. Getting database statistics...")
    stats = db_manager.get_database_stats()
    
    if stats:
        print("📊 Database statistics:")
        print(f"   - Total messages: {stats['message_count']:,}")
        print(f"   - Unique contacts: {stats['contact_count']:,}")
        print(f"   - Database size: {stats['database_size'] / (1024*1024):.1f} MB")
        if stats['earliest_message'] and stats['latest_message']:
            print(f"   - Date range: {stats['earliest_message']} to {stats['latest_message']}")
    else:
        print("⚠️  Could not retrieve database statistics")
    
    print("\n🎉 Messages database copy completed successfully!")
    print(f"   Copy location: {copy_path}")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)