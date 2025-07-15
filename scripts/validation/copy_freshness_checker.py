#!/usr/bin/env python3
"""
Database Copy Freshness Checker

This utility validates that database copies created by the polling service
contain recent messages and are not stale due to WAL file timing issues.

Usage:
    python scripts/validation/copy_freshness_checker.py
    python scripts/validation/copy_freshness_checker.py --continuous --interval 10
    python scripts/validation/copy_freshness_checker.py --threshold 30
"""

import os
import sys
import time
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.database.manager import DatabaseManager
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class CopyFreshnessChecker:
    """Validates database copy freshness and WAL file integration"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.messages_db_path = Path("~/Library/Messages/chat.db").expanduser()
        self.db_manager = DatabaseManager(str(self.data_dir))
        self.freshness_history = []
        
    def get_source_wal_info(self) -> Dict[str, Any]:
        """Get information about the source WAL files"""
        try:
            base_path = self.messages_db_path
            wal_path = base_path.with_suffix('.db-wal')
            shm_path = base_path.with_suffix('.db-shm')
            
            info = {
                "main_db_exists": base_path.exists(),
                "wal_exists": wal_path.exists(),
                "shm_exists": shm_path.exists(),
                "main_db_mtime": None,
                "wal_mtime": None,
                "wal_size": None
            }
            
            if base_path.exists():
                info["main_db_mtime"] = datetime.fromtimestamp(base_path.stat().st_mtime)
            
            if wal_path.exists():
                stat = wal_path.stat()
                info["wal_mtime"] = datetime.fromtimestamp(stat.st_mtime)
                info["wal_size"] = stat.st_size
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get WAL info: {e}")
            return {}
    
    def get_max_rowid_from_source(self) -> Optional[int]:
        """Get maximum ROWID from source Messages database"""
        try:
            with sqlite3.connect(str(self.messages_db_path), timeout=5) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(ROWID) FROM message")
                result = cursor.fetchone()
                return result[0] if result[0] is not None else 0
        except sqlite3.Error as e:
            logger.error(f"Failed to get source max ROWID: {e}")
            return None
    
    def get_max_rowid_from_copy(self, copy_path: Path) -> Optional[int]:
        """Get maximum ROWID from database copy"""
        try:
            with sqlite3.connect(str(copy_path), timeout=5) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(ROWID) FROM message")
                result = cursor.fetchone()
                return result[0] if result[0] is not None else 0
        except sqlite3.Error as e:
            logger.error(f"Failed to get copy max ROWID: {e}")
            return None
    
    def get_recent_messages_from_source(self, minutes_back: int = 5) -> List[Dict[str, Any]]:
        """Get messages from source database within specified time window"""
        try:
            # Apple timestamps are nanoseconds since 2001-01-01
            apple_epoch = datetime(2001, 1, 1)
            cutoff_time = datetime.now() - timedelta(minutes=minutes_back)
            cutoff_timestamp = int((cutoff_time - apple_epoch).total_seconds() * 1_000_000_000)
            
            with sqlite3.connect(str(self.messages_db_path), timeout=5) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT ROWID, text, date, is_from_me, handle_id
                    FROM message 
                    WHERE date > ?
                    ORDER BY ROWID DESC
                    LIMIT 100
                    """,
                    (cutoff_timestamp,)
                )
                
                messages = []
                for row in cursor.fetchall():
                    rowid, text, date, is_from_me, handle_id = row
                    
                    # Convert Apple timestamp back to datetime
                    timestamp_seconds = date / 1_000_000_000
                    message_time = apple_epoch + timedelta(seconds=timestamp_seconds)
                    
                    messages.append({
                        "rowid": rowid,
                        "text": text[:100] if text else "",  # First 100 chars
                        "timestamp": message_time.isoformat(),
                        "is_from_me": bool(is_from_me),
                        "handle_id": handle_id
                    })
                
                return messages
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get recent messages: {e}")
            return []
    
    def validate_copy_freshness(self, freshness_threshold_seconds: int = 30) -> Dict[str, Any]:
        """
        Validate that a database copy contains recent messages
        
        Args:
            freshness_threshold_seconds: Maximum age for copy to be considered fresh
            
        Returns:
            Dictionary with validation results
        """
        validation_start = datetime.now()
        
        try:
            # Get source state before copy
            source_wal_info = self.get_source_wal_info()
            source_max_rowid = self.get_max_rowid_from_source()
            recent_messages = self.get_recent_messages_from_source()
            
            if source_max_rowid is None:
                return {
                    "success": False,
                    "error": "Cannot access source database",
                    "timestamp": validation_start.isoformat()
                }
            
            # Create database copy
            copy_start_time = time.time()
            copy_path = self.db_manager.create_safe_copy()
            copy_creation_time = time.time() - copy_start_time
            
            if not copy_path or not copy_path.exists():
                return {
                    "success": False,
                    "error": "Failed to create database copy",
                    "timestamp": validation_start.isoformat()
                }
            
            # Get copy state
            copy_max_rowid = self.get_max_rowid_from_copy(copy_path)
            copy_creation_datetime = datetime.now()
            
            # Calculate freshness metrics
            rowid_lag = source_max_rowid - copy_max_rowid if copy_max_rowid else float('inf')
            copy_age_seconds = (copy_creation_datetime - validation_start).total_seconds()
            
            # Determine if copy is fresh enough
            is_fresh = (
                copy_max_rowid is not None and
                rowid_lag <= 0 and  # Copy should have at least the same ROWIDs as source
                copy_age_seconds <= freshness_threshold_seconds
            )
            
            # Check if recent messages are in copy
            recent_messages_in_copy = 0
            if recent_messages and copy_path:
                try:
                    recent_rowids = {msg["rowid"] for msg in recent_messages}
                    with sqlite3.connect(str(copy_path), timeout=5) as conn:
                        cursor = conn.cursor()
                        placeholders = ",".join("?" * len(recent_rowids))
                        cursor.execute(
                            f"SELECT COUNT(*) FROM message WHERE ROWID IN ({placeholders})",
                            list(recent_rowids)
                        )
                        recent_messages_in_copy = cursor.fetchone()[0]
                except sqlite3.Error:
                    pass
            
            # Build validation result
            result = {
                "success": True,
                "timestamp": validation_start.isoformat(),
                "source_max_rowid": source_max_rowid,
                "copy_max_rowid": copy_max_rowid,
                "rowid_lag": rowid_lag,
                "copy_creation_time_seconds": copy_creation_time,
                "copy_age_seconds": copy_age_seconds,
                "freshness_threshold_seconds": freshness_threshold_seconds,
                "is_fresh": is_fresh,
                "recent_messages_count": len(recent_messages),
                "recent_messages_in_copy": recent_messages_in_copy,
                "recent_message_coverage": (
                    recent_messages_in_copy / len(recent_messages) 
                    if recent_messages else 1.0
                ),
                "source_wal_info": source_wal_info,
                "copy_path": str(copy_path)
            }
            
            # Add detailed analysis
            if not is_fresh:
                issues = []
                if rowid_lag > 0:
                    issues.append(f"Copy missing {rowid_lag} recent ROWIDs")
                if copy_age_seconds > freshness_threshold_seconds:
                    issues.append(f"Copy creation took {copy_age_seconds:.1f}s (threshold: {freshness_threshold_seconds}s)")
                result["freshness_issues"] = issues
            
            # Clean up copy
            try:
                copy_path.unlink(missing_ok=True)
            except:
                pass
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": validation_start.isoformat()
            }
    
    def run_continuous_monitoring(self, interval_seconds: int = 30, duration_minutes: int = 10):
        """Run continuous copy freshness monitoring"""
        logger.info(f"Starting continuous copy freshness monitoring")
        logger.info(f"Interval: {interval_seconds}s, Duration: {duration_minutes}m")
        
        start_time = time.time()
        duration_seconds = duration_minutes * 60
        test_count = 0
        fresh_count = 0
        
        try:
            while time.time() - start_time < duration_seconds:
                test_count += 1
                logger.info(f"\n--- Freshness Test #{test_count} ---")
                
                result = self.validate_copy_freshness()
                self.freshness_history.append(result)
                
                if result["success"]:
                    if result["is_fresh"]:
                        fresh_count += 1
                        logger.info(f"✓ Copy is fresh (ROWID lag: {result['rowid_lag']}, creation time: {result['copy_creation_time_seconds']:.3f}s)")
                    else:
                        logger.warning(f"⚠️ Copy is stale:")
                        for issue in result.get("freshness_issues", []):
                            logger.warning(f"   - {issue}")
                    
                    # Show recent message coverage
                    coverage = result["recent_message_coverage"]
                    logger.info(f"Recent message coverage: {coverage:.1%} ({result['recent_messages_in_copy']}/{result['recent_messages_count']})")
                    
                else:
                    logger.error(f"❌ Freshness test failed: {result.get('error', 'Unknown error')}")
                
                # Wait for next test
                if time.time() - start_time < duration_seconds:
                    time.sleep(interval_seconds)
        
        except KeyboardInterrupt:
            logger.info("\nMonitoring stopped by user")
        
        # Generate summary report
        logger.info(f"\n=== Continuous Monitoring Summary ===")
        logger.info(f"Total tests: {test_count}")
        logger.info(f"Fresh copies: {fresh_count}")
        logger.info(f"Success rate: {fresh_count/test_count:.1%}" if test_count > 0 else "No tests completed")
        
        if self.freshness_history:
            avg_creation_time = sum(
                r["copy_creation_time_seconds"] for r in self.freshness_history 
                if r["success"]
            ) / len([r for r in self.freshness_history if r["success"]])
            
            logger.info(f"Average copy creation time: {avg_creation_time:.3f}s")
            
            max_rowid_lag = max(
                r.get("rowid_lag", 0) for r in self.freshness_history 
                if r["success"] and r.get("rowid_lag", 0) >= 0
            )
            logger.info(f"Maximum ROWID lag observed: {max_rowid_lag}")
    
    def run_single_test(self, freshness_threshold: int = 30) -> bool:
        """Run a single freshness validation test"""
        logger.info("Running single copy freshness validation...")
        
        result = self.validate_copy_freshness(freshness_threshold)
        
        if not result["success"]:
            logger.error(f"❌ Validation failed: {result.get('error', 'Unknown error')}")
            return False
        
        logger.info(f"Source max ROWID: {result['source_max_rowid']}")
        logger.info(f"Copy max ROWID: {result['copy_max_rowid']}")
        logger.info(f"ROWID lag: {result['rowid_lag']}")
        logger.info(f"Copy creation time: {result['copy_creation_time_seconds']:.3f}s")
        logger.info(f"Recent messages in copy: {result['recent_messages_in_copy']}/{result['recent_messages_count']} ({result['recent_message_coverage']:.1%})")
        
        if result["is_fresh"]:
            logger.info("✓ Copy is fresh and up-to-date")
            return True
        else:
            logger.warning("⚠️ Copy freshness issues detected:")
            for issue in result.get("freshness_issues", []):
                logger.warning(f"   - {issue}")
            return False


def main():
    """Main function with CLI argument parsing"""
    parser = argparse.ArgumentParser(
        description="Database Copy Freshness Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validation/copy_freshness_checker.py
  python scripts/validation/copy_freshness_checker.py --threshold 60
  python scripts/validation/copy_freshness_checker.py --continuous --duration 5 --interval 15
        """
    )
    
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuous monitoring instead of single test"
    )
    
    parser.add_argument(
        "--threshold",
        type=int,
        default=30,
        help="Freshness threshold in seconds (default: 30)"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Interval between tests in continuous mode (seconds, default: 30)"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=10,
        help="Duration for continuous monitoring (minutes, default: 10)"
    )
    
    parser.add_argument(
        "--data-dir",
        default="./data",
        help="Data directory for database files (default: ./data)"
    )
    
    args = parser.parse_args()
    
    # Create checker
    checker = CopyFreshnessChecker(args.data_dir)
    
    try:
        if args.continuous:
            checker.run_continuous_monitoring(args.interval, args.duration)
            return 0
        else:
            success = checker.run_single_test(args.threshold)
            return 0 if success else 1
            
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Checker failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())