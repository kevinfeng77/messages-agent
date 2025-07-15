#!/usr/bin/env python3
"""
Live iMessage Polling Validation

This script validates the real-time iMessage polling system using the actual macOS Messages database.
Unlike the mock validation, this tests real database copy freshness, WAL file integration,
and end-to-end message detection with actual iMessages.

Usage:
    python scripts/validation/validate_live_polling.py --interactive
    python scripts/validation/validate_live_polling.py --duration 5m
    python scripts/validation/validate_live_polling.py --automated
"""

import os
import sys
import time
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import threading
import signal

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.database.polling_service import MessagePollingService
from src.database.manager import DatabaseManager
from src.database.messages_db import MessagesDatabase
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class LivePollingValidator:
    """Validates polling service with real Messages database interaction"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.messages_db_path = "~/Library/Messages/chat.db"
        self.polling_service = None
        self.validation_results = {}
        self.stop_validation = False
        
        # Validation metrics
        self.baseline_rowid = None
        self.messages_detected = []
        self.copy_freshness_tests = []
        self.performance_metrics = []
        
    def check_prerequisites(self) -> bool:
        """Check if system meets requirements for live validation"""
        logger.info("=== Checking Prerequisites ===")
        
        try:
            # Check if Messages database exists and is accessible
            messages_db_path = Path(self.messages_db_path).expanduser()
            if not messages_db_path.exists():
                logger.error(f"Messages database not found at {messages_db_path}")
                return False
            
            # Test database access
            try:
                with sqlite3.connect(str(messages_db_path), timeout=5) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM message LIMIT 1")
                    cursor.fetchone()
                logger.info("✓ Messages database accessible")
            except sqlite3.Error as e:
                logger.error(f"Cannot access Messages database: {e}")
                logger.error("Make sure Messages.app has proper permissions and is not corrupted")
                return False
            
            # Check if we can create database copies
            db_manager = DatabaseManager(str(self.data_dir))
            try:
                copy_path = db_manager.create_safe_copy()
                if copy_path and copy_path.exists():
                    logger.info("✓ Database copy creation works")
                    # Clean up test copy
                    copy_path.unlink(missing_ok=True)
                else:
                    logger.error("Failed to create database copy")
                    return False
            except Exception as e:
                logger.error(f"Database copy creation failed: {e}")
                return False
            
            # Check polling service initialization
            try:
                test_service = MessagePollingService(str(self.data_dir), poll_interval=1)
                if test_service.initialize():
                    logger.info("✓ Polling service initialization works")
                else:
                    logger.error("Polling service initialization failed")
                    return False
            except Exception as e:
                logger.error(f"Polling service setup failed: {e}")
                return False
            
            logger.info("✓ All prerequisites met")
            return True
            
        except Exception as e:
            logger.error(f"Prerequisites check failed: {e}")
            return False
    
    def get_current_max_rowid(self) -> Optional[int]:
        """Get the current maximum ROWID from live Messages database"""
        try:
            messages_db_path = Path(self.messages_db_path).expanduser()
            with sqlite3.connect(str(messages_db_path), timeout=5) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(ROWID) FROM message")
                result = cursor.fetchone()
                return result[0] if result[0] is not None else 0
        except sqlite3.Error as e:
            logger.error(f"Failed to get max ROWID: {e}")
            return None
    
    def get_wal_file_modification_time(self) -> Optional[datetime]:
        """Get WAL file modification time for freshness checks"""
        try:
            wal_path = Path(self.messages_db_path).expanduser().with_suffix('.db-wal')
            if wal_path.exists():
                return datetime.fromtimestamp(wal_path.stat().st_mtime)
            return None
        except Exception as e:
            logger.error(f"Failed to get WAL modification time: {e}")
            return None
    
    def validate_copy_freshness(self) -> bool:
        """Validate that database copies are fresh enough to contain recent messages"""
        logger.info("=== Validating Copy Freshness ===")
        
        try:
            # Get WAL modification time before copy
            wal_time_before = self.get_wal_file_modification_time()
            baseline_rowid = self.get_current_max_rowid()
            
            if baseline_rowid is None:
                logger.error("Cannot get baseline ROWID")
                return False
            
            # Create database copy
            db_manager = DatabaseManager(str(self.data_dir))
            start_time = time.time()
            copy_path = db_manager.create_safe_copy()
            copy_creation_time = time.time() - start_time
            
            if not copy_path or not copy_path.exists():
                logger.error("Failed to create database copy")
                return False
            
            # Check copy contains expected ROWIDs
            try:
                with sqlite3.connect(str(copy_path)) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT MAX(ROWID) FROM message")
                    copy_max_rowid = cursor.fetchone()[0]
                    
                    # Copy should contain at least the baseline ROWID
                    if copy_max_rowid < baseline_rowid:
                        logger.error(f"Copy is stale: contains ROWID {copy_max_rowid}, expected {baseline_rowid}")
                        return False
                    
                    logger.info(f"✓ Copy contains expected ROWIDs: {copy_max_rowid} >= {baseline_rowid}")
                    
            except sqlite3.Error as e:
                logger.error(f"Failed to validate copy contents: {e}")
                return False
            
            # Record freshness metrics
            wal_time_after = self.get_wal_file_modification_time()
            freshness_test = {
                "copy_creation_time_seconds": copy_creation_time,
                "baseline_rowid": baseline_rowid,
                "copy_max_rowid": copy_max_rowid,
                "wal_modified_before": wal_time_before.isoformat() if wal_time_before else None,
                "wal_modified_after": wal_time_after.isoformat() if wal_time_after else None,
                "copy_is_fresh": copy_max_rowid >= baseline_rowid
            }
            
            self.copy_freshness_tests.append(freshness_test)
            
            logger.info(f"✓ Copy creation time: {copy_creation_time:.3f}s")
            logger.info(f"✓ Copy freshness validated")
            
            # Clean up
            copy_path.unlink(missing_ok=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Copy freshness validation failed: {e}")
            return False
    
    def start_polling_service(self) -> bool:
        """Start the polling service for testing"""
        try:
            self.polling_service = MessagePollingService(
                str(self.data_dir), 
                poll_interval=2,  # Fast polling for testing
                batch_size=100
            )
            
            if not self.polling_service.initialize():
                logger.error("Failed to initialize polling service")
                return False
            
            # Set up message detection callback
            def on_new_messages(new_messages, synced_count):
                detection_time = datetime.now()
                for msg in new_messages:
                    self.messages_detected.append({
                        "rowid": msg["rowid"],
                        "detection_time": detection_time.isoformat(),
                        "contents": msg.get("extracted_text", msg.get("text", ""))[:100],  # First 100 chars
                        "is_from_me": msg.get("is_from_me", False)
                    })
                
                logger.info(f"🚨 LIVE DETECTION: {len(new_messages)} new messages, {synced_count} synced")
                for i, msg in enumerate(new_messages[:3]):  # Show first 3
                    content = msg.get("extracted_text", msg.get("text", ""))[:50]
                    sender = "You" if msg.get("is_from_me") else "Contact"
                    logger.info(f"  {i+1}. {sender}: {content}... (ROWID: {msg['rowid']})")
            
            self.polling_service.set_new_message_callback(on_new_messages)
            
            # Start polling in background thread
            self.polling_thread = threading.Thread(target=self.polling_service.start_polling)
            self.polling_thread.daemon = True
            self.polling_thread.start()
            
            logger.info("✓ Polling service started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start polling service: {e}")
            return False
    
    def stop_polling_service(self):
        """Stop the polling service"""
        if self.polling_service:
            self.polling_service.stop_polling()
            logger.info("Polling service stopped")
    
    def validate_interactive_mode(self, duration_minutes: int = 5) -> bool:
        """Interactive validation - prompts user to send messages"""
        logger.info("=== Interactive Message Detection Validation ===")
        
        try:
            # Get baseline
            self.baseline_rowid = self.get_current_max_rowid()
            if self.baseline_rowid is None:
                logger.error("Cannot get baseline ROWID")
                return False
            
            logger.info(f"Baseline ROWID: {self.baseline_rowid}")
            
            # Start polling service
            if not self.start_polling_service():
                return False
            
            # Interactive prompt
            print("\n" + "="*60)
            print("INTERACTIVE LIVE POLLING VALIDATION")
            print("="*60)
            print(f"⏱️  Validation will run for {duration_minutes} minutes")
            print("📱 Please send iMessages to test real-time detection:")
            print("   - Send messages to yourself or others")
            print("   - Try different message types (text, emoji, etc.)")
            print("   - Watch for live detection notifications above")
            print("   - Press Ctrl+C to stop early")
            print("="*60)
            print("\n🔄 Polling service is running... Send some messages!\n")
            
            # Wait for specified duration
            start_time = time.time()
            duration_seconds = duration_minutes * 60
            
            try:
                while time.time() - start_time < duration_seconds and not self.stop_validation:
                    time.sleep(1)
                    
                    # Show periodic status
                    elapsed = int(time.time() - start_time)
                    if elapsed > 0 and elapsed % 30 == 0:  # Every 30 seconds
                        remaining = duration_seconds - elapsed
                        detected_count = len(self.messages_detected)
                        logger.info(f"⏱️  {remaining//60}m {remaining%60}s remaining, {detected_count} messages detected so far")
            
            except KeyboardInterrupt:
                logger.info("\nValidation stopped by user")
            
            # Stop polling
            self.stop_polling_service()
            
            # Analyze results
            detected_count = len(self.messages_detected)
            final_rowid = self.get_current_max_rowid()
            
            logger.info(f"\n=== Validation Results ===")
            logger.info(f"✓ Duration: {(time.time() - start_time):.1f} seconds")
            logger.info(f"✓ Messages detected by polling: {detected_count}")
            logger.info(f"✓ ROWID progression: {self.baseline_rowid} → {final_rowid}")
            
            if detected_count > 0:
                logger.info(f"✓ Live message detection working!")
                for i, msg in enumerate(self.messages_detected[:5]):  # Show first 5
                    logger.info(f"  {i+1}. ROWID {msg['rowid']}: {msg['contents'][:50]}...")
                return True
            else:
                logger.warning("⚠️  No messages detected during validation")
                logger.warning("   This could mean:")
                logger.warning("   - No messages were sent during the test period")
                logger.warning("   - Polling service has detection issues")
                logger.warning("   - Database copy staleness problems")
                return False
            
        except Exception as e:
            logger.error(f"Interactive validation failed: {e}")
            return False
    
    def validate_performance_metrics(self) -> bool:
        """Validate polling performance characteristics"""
        logger.info("=== Validating Performance Metrics ===")
        
        try:
            # Test multiple copy creation cycles
            copy_times = []
            db_manager = DatabaseManager(str(self.data_dir))
            
            for i in range(5):
                start_time = time.time()
                copy_path = db_manager.create_safe_copy()
                copy_time = time.time() - start_time
                copy_times.append(copy_time)
                
                if copy_path and copy_path.exists():
                    copy_path.unlink(missing_ok=True)
                
                logger.info(f"Copy {i+1}: {copy_time:.3f}s")
            
            avg_copy_time = sum(copy_times) / len(copy_times)
            max_copy_time = max(copy_times)
            
            # Performance thresholds
            poll_interval = 2.0  # Default polling interval
            copy_efficiency = avg_copy_time / poll_interval
            
            logger.info(f"✓ Average copy time: {avg_copy_time:.3f}s")
            logger.info(f"✓ Max copy time: {max_copy_time:.3f}s")
            logger.info(f"✓ Copy efficiency: {copy_efficiency:.1%} of polling interval")
            
            self.performance_metrics = {
                "avg_copy_time_seconds": avg_copy_time,
                "max_copy_time_seconds": max_copy_time,
                "poll_interval_seconds": poll_interval,
                "copy_efficiency_ratio": copy_efficiency,
                "performance_acceptable": copy_efficiency < 0.5  # Copy should be <50% of poll interval
            }
            
            if copy_efficiency > 0.5:
                logger.warning(f"⚠️  Copy creation is slow: {copy_efficiency:.1%} of polling interval")
                logger.warning("   This may cause missed messages during high-frequency polling")
            else:
                logger.info("✓ Copy performance is acceptable")
            
            return True
            
        except Exception as e:
            logger.error(f"Performance validation failed: {e}")
            return False
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "validation_type": "live_polling",
            "baseline_rowid": self.baseline_rowid,
            "messages_detected": len(self.messages_detected),
            "copy_freshness_tests": self.copy_freshness_tests,
            "performance_metrics": self.performance_metrics,
            "detected_messages": self.messages_detected[:10],  # First 10 messages
            "recommendations": []
        }
        
        # Add recommendations based on results
        if len(self.messages_detected) == 0:
            report["recommendations"].append("No messages detected - verify polling service and database copy freshness")
        
        if self.performance_metrics.get("copy_efficiency_ratio", 0) > 0.5:
            report["recommendations"].append("Copy creation is slow - consider optimizing database copy strategy")
        
        if len(self.copy_freshness_tests) > 0:
            fresh_copies = sum(1 for test in self.copy_freshness_tests if test["copy_is_fresh"])
            if fresh_copies < len(self.copy_freshness_tests):
                report["recommendations"].append("Some database copies were stale - investigate WAL file handling")
        
        return report
    
    def run_validation(self, mode: str = "interactive", duration_minutes: int = 5) -> bool:
        """Run the complete live polling validation"""
        logger.info("Starting Live iMessage Polling Validation")
        logger.info("="*60)
        
        try:
            # Check prerequisites
            if not self.check_prerequisites():
                logger.error("Prerequisites not met - cannot continue")
                return False
            
            # Validate copy freshness
            if not self.validate_copy_freshness():
                logger.error("Copy freshness validation failed")
                return False
            
            # Validate performance
            if not self.validate_performance_metrics():
                logger.error("Performance validation failed")
                return False
            
            # Run main validation based on mode
            success = False
            if mode == "interactive":
                success = self.validate_interactive_mode(duration_minutes)
            elif mode == "automated":
                logger.warning("Automated mode not yet implemented - falling back to interactive")
                success = self.validate_interactive_mode(duration_minutes)
            else:
                logger.error(f"Unknown validation mode: {mode}")
                return False
            
            # Generate report
            report = self.generate_validation_report()
            
            logger.info("\n" + "="*60)
            logger.info("LIVE POLLING VALIDATION REPORT")
            logger.info("="*60)
            logger.info(f"Messages Detected: {report['messages_detected']}")
            logger.info(f"Copy Freshness Tests: {len(report['copy_freshness_tests'])}")
            logger.info(f"Performance Acceptable: {report['performance_metrics'].get('performance_acceptable', 'Unknown')}")
            
            if report["recommendations"]:
                logger.info("\nRecommendations:")
                for rec in report["recommendations"]:
                    logger.info(f"  • {rec}")
            
            if success:
                logger.info("\n🎉 LIVE POLLING VALIDATION PASSED!")
                logger.info("Real-time message detection is working correctly.")
            else:
                logger.error("\n❌ LIVE POLLING VALIDATION FAILED!")
                logger.error("Issues detected with real-time message polling.")
            
            return success
            
        except KeyboardInterrupt:
            logger.info("\nValidation interrupted by user")
            self.stop_polling_service()
            return False
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            self.stop_polling_service()
            return False


def main():
    """Main function with CLI argument parsing"""
    parser = argparse.ArgumentParser(
        description="Live iMessage Polling Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validation/validate_live_polling.py --interactive --duration 3
  python scripts/validation/validate_live_polling.py --automated
  python scripts/validation/validate_live_polling.py --interactive --duration 10
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["interactive", "automated"],
        default="interactive",
        help="Validation mode: interactive (user sends messages) or automated"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=5,
        help="Duration in minutes for validation (default: 5)"
    )
    
    parser.add_argument(
        "--data-dir",
        default="./data",
        help="Data directory for database files (default: ./data)"
    )
    
    # Handle legacy flags
    parser.add_argument(
        "--interactive",
        action="store_const",
        const="interactive",
        dest="mode",
        help="Run in interactive mode (same as --mode interactive)"
    )
    
    parser.add_argument(
        "--automated",
        action="store_const", 
        const="automated",
        dest="mode",
        help="Run in automated mode (same as --mode automated)"
    )
    
    args = parser.parse_args()
    
    # Setup signal handler for graceful shutdown
    validator = LivePollingValidator(args.data_dir)
    
    def signal_handler(signum, frame):
        logger.info("\nReceived interrupt signal, stopping validation...")
        validator.stop_validation = True
        validator.stop_polling_service()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run validation
    try:
        success = validator.run_validation(args.mode, args.duration)
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())