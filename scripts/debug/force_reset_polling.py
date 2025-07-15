#!/usr/bin/env python3
"""
Force Reset Polling State to Current Maximum ROWID (Non-Interactive)

This script automatically sets the polling state to the current maximum ROWID 
in the source Messages database, so that only truly new messages will be detected.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.database.manager import DatabaseManager
from src.database.messages_db import MessagesDatabase
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


def get_current_max_rowid() -> int:
    """Get the current maximum ROWID from the source Messages database"""
    try:
        db_manager = DatabaseManager("./data")
        copy_path = db_manager.create_safe_copy()
        
        if not copy_path:
            logger.error("Failed to create database copy")
            return 0
        
        with sqlite3.connect(str(copy_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(ROWID) FROM message")
            result = cursor.fetchone()
            max_rowid = result[0] if result and result[0] else 0
            
        logger.info(f"Current maximum ROWID in source database: {max_rowid}")
        return max_rowid
        
    except Exception as e:
        logger.error(f"Error getting max ROWID: {e}")
        return 0


def reset_polling_state(new_rowid: int) -> bool:
    """Reset the polling state to the specified ROWID"""
    try:
        messages_db = MessagesDatabase("./data/messages.db")
        
        # Get current state
        current_state = messages_db.get_polling_state()
        if not current_state:
            logger.error("No polling state found")
            return False
            
        old_rowid = current_state["last_processed_rowid"]
        
        # Update polling state
        success = messages_db.update_polling_state(
            last_processed_rowid=new_rowid,
            messages_processed_count=0,  # Reset counter since we're skipping
            sync_status="idle"
        )
        
        if success:
            logger.info(f"✅ Polling state updated:")
            logger.info(f"   Old ROWID: {old_rowid}")
            logger.info(f"   New ROWID: {new_rowid}")
            logger.info(f"   Skipped: {new_rowid - old_rowid} messages")
            return True
        else:
            logger.error("Failed to update polling state")
            return False
            
    except Exception as e:
        logger.error(f"Error resetting polling state: {e}")
        return False


def main():
    """Main function"""
    print("🔄 Force Reset Polling State to Current Maximum ROWID")
    print("=" * 60)
    
    # Check if database exists
    db_path = Path("./data/messages.db")
    if not db_path.exists():
        print("❌ Error: Database file not found at ./data/messages.db")
        print("Please run the polling service at least once to initialize.")
        return 1
    
    # Get current max ROWID from source
    print("📊 Checking current maximum ROWID in source database...")
    max_rowid = get_current_max_rowid()
    
    if max_rowid == 0:
        print("❌ Error: Could not determine maximum ROWID")
        return 1
    
    print(f"   Maximum ROWID found: {max_rowid}")
    
    # Show current polling state
    print("\n📋 Current polling state:")
    messages_db = MessagesDatabase("./data/messages.db")
    current_state = messages_db.get_polling_state()
    
    if current_state:
        old_rowid = current_state['last_processed_rowid']
        print(f"   Last processed ROWID: {old_rowid}")
        print(f"   Total processed: {current_state['total_messages_processed']}")
        print(f"   Sync status: {current_state['sync_status']}")
        
        messages_to_skip = max_rowid - old_rowid
        print(f"   Messages to skip: {messages_to_skip}")
        
        if messages_to_skip <= 0:
            print("\n✅ Polling state is already up to date!")
            print("   No reset needed.")
            return 0
            
    else:
        print("   ❌ No polling state found")
        return 1
    
    # Automatically reset the polling state
    print(f"\n🔄 Automatically resetting polling state to ROWID {max_rowid}...")
    print("   This will make the service only detect truly new messages.")
    
    if reset_polling_state(max_rowid):
        print("\n✅ Polling state reset successfully!")
        print(f"   Now positioned at ROWID {max_rowid}")
        print("   The service will only detect messages received after this point.")
        print("\n🚀 Ready to start polling:")
        print("     python scripts/run_polling_service.py start")
        print("     # or")
        print("     python polling_main.py")
        return 0
    else:
        print("\n❌ Failed to reset polling state")
        return 1


if __name__ == "__main__":
    sys.exit(main())