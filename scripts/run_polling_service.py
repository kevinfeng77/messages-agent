#!/usr/bin/env python3
"""
CLI script to run the iMessage polling service

This script provides a command-line interface for starting and managing
the real-time iMessage polling service.
"""

import argparse
import os
import sys
import signal
import time
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database.polling_service import MessagePollingService
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    logger.info("\nReceived interrupt signal, stopping polling service...")
    sys.exit(0)


def print_status(polling_service: MessagePollingService):
    """Print current service status"""
    status = polling_service.get_status()
    
    print("\n" + "=" * 50)
    print("POLLING SERVICE STATUS")
    print("=" * 50)
    print(f"Running: {'Yes' if status['is_running'] else 'No'}")
    print(f"Poll Interval: {status['poll_interval']}s")
    print(f"Batch Size: {status['batch_size']}")
    
    if status.get("last_error"):
        print(f"Last Error: {status['last_error']}")
    
    polling_state = status.get("polling_state")
    if polling_state:
        print(f"\nDatabase State:")
        print(f"  Last Processed ROWID: {polling_state['last_processed_rowid']}")
        print(f"  Total Messages Processed: {polling_state['total_messages_processed']}")
        print(f"  Sync Status: {polling_state['sync_status']}")
        print(f"  Last Sync: {polling_state['last_sync_timestamp']}")
    
    print("=" * 50)


def run_single_poll(data_dir: str, batch_size: int) -> bool:
    """Run a single polling cycle and display results"""
    print("Running single polling cycle...")
    
    try:
        polling_service = MessagePollingService(
            data_dir=data_dir,
            poll_interval=5,
            batch_size=batch_size
        )
        
        # Initialize if needed
        if not polling_service.initialize():
            print("❌ Failed to initialize polling service")
            return False
        
        # Run single poll
        start_time = time.time()
        result = polling_service.poll_once()
        duration = time.time() - start_time
        
        print(f"\nPoll completed in {duration:.2f}s")
        
        if result["success"]:
            print("✅ Poll successful")
            print(f"   New messages found: {result['new_messages']}")
            print(f"   Messages synced: {result['synced_messages']}")
            print(f"   Last processed ROWID: {result['last_processed_rowid']}")
        else:
            print("❌ Poll failed")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            return False
        
        # Show status
        print_status(polling_service)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during single poll: {e}")
        return False


def run_continuous_polling(data_dir: str, poll_interval: int, batch_size: int):
    """Run continuous polling with status updates"""
    print(f"Starting continuous polling (interval: {poll_interval}s, batch_size: {batch_size})")
    
    try:
        polling_service = MessagePollingService(
            data_dir=data_dir,
            poll_interval=poll_interval,
            batch_size=batch_size
        )
        
        # Initialize service
        if not polling_service.initialize():
            print("❌ Failed to initialize polling service")
            return
        
        print("✅ Polling service initialized")
        print_status(polling_service)
        
        print(f"\nStarting continuous polling... (Press Ctrl+C to stop)")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start polling in separate thread and monitor
        import threading
        
        def monitor_polling():
            poll_count = 0
            last_status_time = time.time()
            
            while polling_service.is_running:
                time.sleep(1)
                
                # Print status every 30 seconds
                current_time = time.time()
                if current_time - last_status_time >= 30:
                    status = polling_service.get_status()
                    state = status.get("polling_state", {})
                    print(f"\n📊 Status Update (Poll #{poll_count}):")
                    print(f"   Last ROWID: {state.get('last_processed_rowid', 'N/A')}")
                    print(f"   Total Processed: {state.get('total_messages_processed', 'N/A')}")
                    print(f"   Sync Status: {state.get('sync_status', 'N/A')}")
                    
                    if status.get("last_error"):
                        print(f"   ⚠️  Last Error: {status['last_error']}")
                    
                    last_status_time = current_time
                    poll_count += 1
        
        # Start monitoring in background
        monitor_thread = threading.Thread(target=monitor_polling, daemon=True)
        monitor_thread.start()
        
        # Start polling (blocks until stopped)
        polling_service.start_polling()
        
    except KeyboardInterrupt:
        print("\n🛑 Received interrupt, stopping...")
    except Exception as e:
        print(f"❌ Error during continuous polling: {e}")
    finally:
        if 'polling_service' in locals():
            polling_service.stop_polling()
        print("🏁 Polling service stopped")


def show_current_status(data_dir: str):
    """Show current status without starting polling"""
    try:
        polling_service = MessagePollingService(data_dir=data_dir)
        
        # Check if service has been initialized
        messages_db_path = Path(data_dir) / "messages.db"
        if not messages_db_path.exists():
            print("❌ Polling service has not been initialized")
            print(f"   No database found at: {messages_db_path}")
            return
        
        print_status(polling_service)
        
        # Show database statistics
        from src.database.messages_db import MessagesDatabase
        messages_db = MessagesDatabase(str(messages_db_path))
        
        if messages_db.database_exists():
            stats = messages_db.get_database_stats()
            print(f"\nDatabase Statistics:")
            print(f"  Users: {stats.get('total_users', 'N/A')}")
            print(f"  Database Size: {stats.get('database_size_bytes', 0) / 1024:.1f} KB")
        
    except Exception as e:
        print(f"❌ Error showing status: {e}")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="iMessage Polling Service CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status                          # Show current status
  %(prog)s poll                            # Run single poll cycle
  %(prog)s start                           # Start continuous polling
  %(prog)s start --interval 10 --batch 50 # Custom polling settings
        """
    )
    
    parser.add_argument(
        "command",
        choices=["status", "poll", "start"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--data-dir",
        default="./data",
        help="Directory for database files (default: ./data)"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Polling interval in seconds (default: 5)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int, 
        default=100,
        help="Maximum messages to process per batch (default: 100)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Ensure data directory exists
    data_dir = Path(args.data_dir)
    data_dir.mkdir(exist_ok=True)
    
    print("🔄 iMessage Polling Service CLI")
    print(f"📁 Data Directory: {data_dir.absolute()}")
    
    # Execute command
    if args.command == "status":
        show_current_status(str(data_dir))
    
    elif args.command == "poll":
        success = run_single_poll(str(data_dir), args.batch_size)
        sys.exit(0 if success else 1)
    
    elif args.command == "start":
        run_continuous_polling(str(data_dir), args.interval, args.batch_size)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()