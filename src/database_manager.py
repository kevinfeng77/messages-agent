"""Database Manager - Safe copying and WAL handling for Messages database"""

import os
import shutil
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages safe copying and access to the Messages database"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # macOS Messages database location
        self.source_db_path = Path.home() / "Library/Messages/chat.db"
        self.source_wal_path = self.source_db_path.with_suffix(".db-wal")
        self.source_shm_path = self.source_db_path.with_suffix(".db-shm")
        
        # Working copy paths
        self.copy_db_path = self.data_dir / "chat_copy.db"
        self.copy_wal_path = self.copy_db_path.with_suffix(".db-wal")
        self.copy_shm_path = self.copy_db_path.with_suffix(".db-shm")
        
    def verify_source_database(self) -> bool:
        """Verify that the source Messages database exists and is accessible"""
        if not self.source_db_path.exists():
            logger.error(f"Messages database not found at {self.source_db_path}")
            return False
            
        if not os.access(self.source_db_path, os.R_OK):
            logger.error(f"No read permission for Messages database at {self.source_db_path}")
            return False
            
        return True
    
    def copy_database_files(self) -> bool:
        """Copy all database files (main, WAL, and SHM) to working directory"""
        try:
            # Copy main database file
            if self.source_db_path.exists():
                shutil.copy2(self.source_db_path, self.copy_db_path)
                logger.info(f"Copied main database to {self.copy_db_path}")
            else:
                logger.error("Main database file not found")
                return False
            
            # Copy WAL file if it exists
            if self.source_wal_path.exists():
                shutil.copy2(self.source_wal_path, self.copy_wal_path)
                logger.info(f"Copied WAL file to {self.copy_wal_path}")
            
            # Copy SHM file if it exists
            if self.source_shm_path.exists():
                shutil.copy2(self.source_shm_path, self.copy_shm_path)
                logger.info(f"Copied SHM file to {self.copy_shm_path}")
                
            return True
            
        except PermissionError as e:
            logger.error(f"Permission denied while copying database files: {e}")
            return False
        except Exception as e:
            logger.error(f"Error copying database files: {e}")
            return False
    
    def checkpoint_database(self) -> bool:
        """Merge WAL file into main database using checkpoint"""
        try:
            conn = sqlite3.connect(str(self.copy_db_path))
            cursor = conn.cursor()
            
            # Execute checkpoint to merge WAL into main database
            cursor.execute("PRAGMA wal_checkpoint(FULL)")
            result = cursor.fetchone()
            
            if result:
                logger.info(f"Checkpoint complete: {result}")
            
            conn.close()
            
            # Remove WAL and SHM files after successful checkpoint
            if self.copy_wal_path.exists():
                self.copy_wal_path.unlink()
            if self.copy_shm_path.exists():
                self.copy_shm_path.unlink()
                
            return True
            
        except sqlite3.Error as e:
            logger.error(f"SQLite error during checkpoint: {e}")
            return False
        except Exception as e:
            logger.error(f"Error during checkpoint: {e}")
            return False
    
    def create_safe_copy(self) -> Optional[Path]:
        """Create a safe working copy of the Messages database"""
        logger.info("Creating safe copy of Messages database...")
        
        if not self.verify_source_database():
            return None
        
        if not self.copy_database_files():
            return None
        
        if not self.checkpoint_database():
            logger.warning("Checkpoint failed, but database copy may still be usable")
        
        logger.info(f"Safe database copy created at {self.copy_db_path}")
        return self.copy_db_path
    
    def get_database_stats(self) -> Optional[dict]:
        """Get basic statistics about the copied database"""
        if not self.copy_db_path.exists():
            logger.error("Database copy does not exist")
            return None
            
        try:
            conn = sqlite3.connect(str(self.copy_db_path))
            cursor = conn.cursor()
            
            # Get message count
            cursor.execute("SELECT COUNT(*) FROM message")
            message_count = cursor.fetchone()[0]
            
            # Get contact count
            cursor.execute("SELECT COUNT(DISTINCT handle_id) FROM message")
            contact_count = cursor.fetchone()[0]
            
            # Get date range
            cursor.execute("SELECT MIN(date), MAX(date) FROM message")
            min_date, max_date = cursor.fetchone()
            
            conn.close()
            
            return {
                "message_count": message_count,
                "contact_count": contact_count,
                "earliest_message": min_date,
                "latest_message": max_date,
                "database_size": self.copy_db_path.stat().st_size
            }
            
        except sqlite3.Error as e:
            logger.error(f"Error getting database stats: {e}")
            return None
    
    def get_last_modification_time(self) -> Optional[datetime]:
        """Get the last modification time of the source WAL file"""
        if self.source_wal_path.exists():
            return datetime.fromtimestamp(self.source_wal_path.stat().st_mtime)
        elif self.source_db_path.exists():
            return datetime.fromtimestamp(self.source_db_path.stat().st_mtime)
        return None
    
    def cleanup_copies(self):
        """Remove all copied database files"""
        for path in [self.copy_db_path, self.copy_wal_path, self.copy_shm_path]:
            if path.exists():
                path.unlink()
                logger.info(f"Removed {path}")