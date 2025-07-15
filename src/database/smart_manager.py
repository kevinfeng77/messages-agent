"""
Smart Database Manager - Enhanced database copying with optimization and freshness validation

This module extends the basic DatabaseManager with intelligent copy reuse,
WAL file monitoring, and copy freshness validation to optimize polling performance
and ensure reliable message detection.
"""

import os
import sqlite3
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from .manager import DatabaseManager
from ..utils.logger_config import get_logger

logger = get_logger(__name__)


class SmartDatabaseManager(DatabaseManager):
    """Enhanced database manager with copy optimization and freshness validation"""
    
    def __init__(self, data_dir: str = "./data", copy_cache_ttl_seconds: int = 60):
        """
        Initialize smart database manager
        
        Args:
            data_dir: Directory for database files
            copy_cache_ttl_seconds: How long to reuse copies before recreating (default: 60s)
        """
        super().__init__(data_dir)
        self.copy_cache_ttl = copy_cache_ttl_seconds
        self.last_copy_info = None  # Cache info about last copy created
        
    def get_source_wal_state(self) -> Dict[str, Any]:
        """Get current state of source database WAL files"""
        try:
            source_path = Path(self.source_path)
            wal_path = source_path.with_suffix('.db-wal')
            shm_path = source_path.with_suffix('.db-shm')
            
            state = {
                "main_db_exists": source_path.exists(),
                "wal_exists": wal_path.exists(),
                "shm_exists": shm_path.exists(),
                "main_db_mtime": None,
                "wal_mtime": None,
                "wal_size": 0,
                "state_timestamp": datetime.now()
            }
            
            if source_path.exists():
                state["main_db_mtime"] = datetime.fromtimestamp(source_path.stat().st_mtime)
            
            if wal_path.exists():
                wal_stat = wal_path.stat()
                state["wal_mtime"] = datetime.fromtimestamp(wal_stat.st_mtime)
                state["wal_size"] = wal_stat.st_size
            
            return state
            
        except Exception as e:
            logger.error(f"Failed to get WAL state: {e}")
            return {"error": str(e), "state_timestamp": datetime.now()}
    
    def has_source_changed_since_copy(self, copy_info: Dict[str, Any]) -> bool:
        """
        Check if source database has changed since the last copy was created
        
        Args:
            copy_info: Information about the last copy (from self.last_copy_info)
            
        Returns:
            True if source has changed and copy should be recreated
        """
        try:
            current_wal_state = self.get_source_wal_state()
            
            if "error" in current_wal_state:
                # If we can't determine state, assume changed to be safe
                return True
            
            # Check if WAL file has been modified
            current_wal_mtime = current_wal_state.get("wal_mtime")
            copy_wal_mtime = copy_info.get("source_wal_state", {}).get("wal_mtime")
            
            if current_wal_mtime != copy_wal_mtime:
                logger.debug(f"WAL file modified: {copy_wal_mtime} -> {current_wal_mtime}")
                return True
            
            # Check if WAL file size has changed
            current_wal_size = current_wal_state.get("wal_size", 0)
            copy_wal_size = copy_info.get("source_wal_state", {}).get("wal_size", 0)
            
            if current_wal_size != copy_wal_size:
                logger.debug(f"WAL size changed: {copy_wal_size} -> {current_wal_size}")
                return True
            
            # Check if main database has been modified
            current_main_mtime = current_wal_state.get("main_db_mtime")
            copy_main_mtime = copy_info.get("source_wal_state", {}).get("main_db_mtime")
            
            if current_main_mtime != copy_main_mtime:
                logger.debug(f"Main DB modified: {copy_main_mtime} -> {current_main_mtime}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking source changes: {e}")
            return True  # Assume changed on error
    
    def is_copy_fresh_enough(self, copy_info: Dict[str, Any]) -> bool:
        """
        Check if existing copy is fresh enough to reuse
        
        Args:
            copy_info: Information about the existing copy
            
        Returns:
            True if copy can be reused, False if should recreate
        """
        try:
            # Check if copy file still exists
            copy_path = Path(copy_info.get("copy_path", ""))
            if not copy_path.exists():
                logger.debug("Copy file no longer exists")
                return False
            
            # Check age of copy
            copy_creation_time = copy_info.get("creation_time")
            if not copy_creation_time:
                logger.debug("No creation time for copy")
                return False
            
            copy_age = (datetime.now() - copy_creation_time).total_seconds()
            if copy_age > self.copy_cache_ttl:
                logger.debug(f"Copy too old: {copy_age:.1f}s > {self.copy_cache_ttl}s")
                return False
            
            # Check if source has changed since copy
            if self.has_source_changed_since_copy(copy_info):
                logger.debug("Source changed since copy")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking copy freshness: {e}")
            return False
    
    def validate_copy_contents(self, copy_path: Path, expected_min_rowid: Optional[int] = None) -> bool:
        """
        Validate that copy contains expected content
        
        Args:
            copy_path: Path to the copy to validate
            expected_min_rowid: Minimum ROWID the copy should contain
            
        Returns:
            True if copy is valid, False otherwise
        """
        try:
            with sqlite3.connect(str(copy_path), timeout=5) as conn:
                cursor = conn.cursor()
                
                # Check if message table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message'")
                if not cursor.fetchone():
                    logger.error("Copy missing message table")
                    return False
                
                # Check if we can query the table
                cursor.execute("SELECT COUNT(*) FROM message")
                message_count = cursor.fetchone()[0]
                
                if message_count == 0:
                    logger.warning("Copy has no messages")
                    return False
                
                # Check maximum ROWID if we have a minimum expectation
                if expected_min_rowid is not None:
                    cursor.execute("SELECT MAX(ROWID) FROM message")
                    max_rowid = cursor.fetchone()[0]
                    
                    if max_rowid is None or max_rowid < expected_min_rowid:
                        logger.error(f"Copy max ROWID {max_rowid} < expected {expected_min_rowid}")
                        return False
                
                logger.debug(f"Copy validation passed: {message_count} messages, max ROWID: {max_rowid if expected_min_rowid else 'not checked'}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Copy validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Copy validation error: {e}")
            return False
    
    def get_fresh_copy_if_needed(self, force_refresh: bool = False) -> Optional[Path]:
        """
        Get a fresh database copy, reusing existing copy if it's still fresh
        
        Args:
            force_refresh: If True, always create new copy regardless of freshness
            
        Returns:
            Path to database copy, or None if failed
        """
        try:
            # Check if we can reuse existing copy
            if not force_refresh and self.last_copy_info and self.is_copy_fresh_enough(self.last_copy_info):
                copy_path = Path(self.last_copy_info["copy_path"])
                if copy_path.exists():
                    logger.debug(f"Reusing fresh copy: {copy_path}")
                    return copy_path
                else:
                    logger.debug("Cached copy path no longer exists")
                    self.last_copy_info = None
            
            # Create new copy
            logger.debug("Creating new database copy")
            copy_creation_start = time.time()
            
            # Get source state before copying
            source_wal_state = self.get_source_wal_state()
            
            # Get current max ROWID for validation
            expected_min_rowid = None
            try:
                with sqlite3.connect(self.source_path, timeout=5) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT MAX(ROWID) FROM message")
                    result = cursor.fetchone()
                    expected_min_rowid = result[0] if result[0] is not None else 0
            except sqlite3.Error:
                pass  # Continue without validation if source inaccessible
            
            # Create the copy using parent method
            copy_path = self.create_safe_copy()
            copy_creation_time = time.time() - copy_creation_start
            
            if not copy_path:
                logger.error("Failed to create database copy")
                return None
            
            # Validate copy contents
            if not self.validate_copy_contents(copy_path, expected_min_rowid):
                logger.error("Copy validation failed")
                try:
                    copy_path.unlink(missing_ok=True)
                except:
                    pass
                return None
            
            # Cache copy information for reuse
            self.last_copy_info = {
                "copy_path": str(copy_path),
                "creation_time": datetime.now(),
                "creation_duration_seconds": copy_creation_time,
                "source_wal_state": source_wal_state,
                "expected_min_rowid": expected_min_rowid
            }
            
            logger.debug(f"Created fresh copy in {copy_creation_time:.3f}s: {copy_path}")
            return copy_path
            
        except Exception as e:
            logger.error(f"Error getting fresh copy: {e}")
            return None
    
    def cleanup_old_copies(self, keep_current: bool = True) -> int:
        """
        Clean up old database copies to free disk space
        
        Args:
            keep_current: If True, keep the currently cached copy
            
        Returns:
            Number of files cleaned up
        """
        try:
            copy_dir = Path(self.data_dir) / "copy"
            if not copy_dir.exists():
                return 0
            
            current_copy_path = None
            if keep_current and self.last_copy_info:
                current_copy_path = Path(self.last_copy_info["copy_path"])
            
            cleaned_count = 0
            for copy_file in copy_dir.glob("chat_copy*.db*"):
                if current_copy_path and copy_file.samefile(current_copy_path):
                    continue  # Keep current copy
                
                try:
                    copy_file.unlink()
                    cleaned_count += 1
                    logger.debug(f"Cleaned up old copy: {copy_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up {copy_file}: {e}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up copies: {e}")
            return 0
    
    def get_copy_efficiency_stats(self) -> Dict[str, Any]:
        """Get statistics about copy reuse efficiency"""
        if not self.last_copy_info:
            return {"no_copy_info": True}
        
        copy_age = (datetime.now() - self.last_copy_info["creation_time"]).total_seconds()
        
        return {
            "last_copy_age_seconds": copy_age,
            "copy_cache_ttl_seconds": self.copy_cache_ttl,
            "copy_utilization": min(copy_age / self.copy_cache_ttl, 1.0),
            "creation_duration_seconds": self.last_copy_info.get("creation_duration_seconds"),
            "copy_is_reusable": self.is_copy_fresh_enough(self.last_copy_info)
        }
    
    def force_refresh_copy(self) -> Optional[Path]:
        """Force creation of a new database copy"""
        return self.get_fresh_copy_if_needed(force_refresh=True)