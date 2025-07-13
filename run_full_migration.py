#!/usr/bin/env python3
"""Run full migration automatically"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from message_migration import migrate_database
from logger_config import setup_logging

def run_full_migration():
    """Run the complete migration process"""
    setup_logging()
    
    db_path = "data/chat_copy.db"
    
    print("🚀 Starting full message migration...")
    print("This will decode ~95,000 messages from attributedBody data")
    
    # Run complete migration
    success = migrate_database(
        db_path=db_path,
        create_backup=True,
        batch_size=1000,
        max_batches=None  # Process all messages
    )
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("All messages with null text but populated attributedBody have been processed.")
    else:
        print("\n❌ Migration failed. Check logs for details.")
        
    return success

if __name__ == "__main__":
    run_full_migration()