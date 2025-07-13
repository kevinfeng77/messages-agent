#!/usr/bin/env python3
"""
Migration script to add handle_id column to existing users table

This script safely adds the handle_id column to the existing users table
without losing any existing data.
"""

import sys
import sqlite3
from pathlib import Path

# Add src to path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from src.database.messages_db import MessagesDatabase
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


def migrate_add_handle_id_column(db_path: str = "./data/messages.db") -> bool:
    """
    Add handle_id column to users table if it doesn't exist
    
    Args:
        db_path: Path to the messages database
        
    Returns:
        True if successful, False otherwise
    """
    db_path = Path(db_path)
    
    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        return False
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            
            # Check if handle_id column already exists
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'handle_id' in column_names:
                logger.info("handle_id column already exists, no migration needed")
                return True
            
            # Add handle_id column
            logger.info("Adding handle_id column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN handle_id INTEGER")
            
            # Create index for handle_id
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_handle_id ON users(handle_id)")
            
            conn.commit()
            logger.info("Successfully added handle_id column and index")
            return True
            
    except sqlite3.Error as e:
        logger.error(f"Error migrating database: {e}")
        return False


def main():
    """Main execution function"""
    print("Migrating messages database to add handle_id column...")
    
    success = migrate_add_handle_id_column()
    
    if success:
        print("✅ Migration completed successfully")
        
        # Verify the migration
        db = MessagesDatabase()
        schema = db.get_table_schema('users')
        if schema:
            column_names = [col[1] for col in schema]
            if 'handle_id' in column_names:
                print("✅ handle_id column verified in schema")
            else:
                print("❌ handle_id column not found after migration")
                return 1
        
        return 0
    else:
        print("❌ Migration failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())