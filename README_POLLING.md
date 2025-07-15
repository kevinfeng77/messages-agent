# iMessage Real-time Polling Service

This implementation provides real-time monitoring of your iMessage database with instant notifications when new messages arrive.

## 🚀 How to Use

### Option 1: Simple CLI Commands

```bash
# Navigate to the implementation directory
cd /Users/nick/Projects/messages-agent/worktrees/imessage-polling

# Check current status
python scripts/run_polling_service.py status

# Run a single poll (one-time check)
python scripts/run_polling_service.py poll

# Start continuous polling with notifications
python scripts/run_polling_service.py start
```

### Option 2: Enhanced Notification Experience

```bash
# Use the enhanced version with rich notifications
python polling_main.py
```

## 📱 What Happens During Continuous Polling

When you start continuous polling, the service will:

1. **Initialize**: Set up database connections and state tracking
2. **Monitor**: Check for new messages every few seconds (configurable)
3. **Notify**: When new messages arrive, you'll see:

```
🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨
📱 NEW MESSAGES DETECTED! (3 found, 2 synced)
🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨

  1. 📥 John Smith at 2:30:45 PM
     💬 Hey, are you free for dinner tonight?
     🆔 ROWID: 12345

  2. 📤 You at 2:31:02 PM
     💬 Sure! What time works for you?
     🆔 ROWID: 12346

============================================
⏰ Last checked: 2:31:15 PM
🔄 Continuing to monitor for new messages...
   Press Ctrl+C to stop
============================================
```

## ⚙️ Configuration Options

### Polling Intervals
```bash
# Check every 10 seconds (default is 5)
python scripts/run_polling_service.py start --interval 10

# Process up to 50 messages per batch (default is 100)
python scripts/run_polling_service.py start --batch-size 50

# Use custom data directory
python scripts/run_polling_service.py start --data-dir /path/to/data
```

### Fast Notifications (Recommended)
```bash
# Check every 1 second for fast notifications (default)
python scripts/run_polling_service.py start

# Safer polling every 2 seconds (recommended if Messages.app is running)
python scripts/run_polling_service.py start --interval 2

# Ultra-fast polling every 0.5 seconds (use only when Messages.app is closed)
python ultra_fast_polling.py
```

## 🔧 Technical Details

### Understanding Message Detection Delays

**Why there's a delay between receiving a message and seeing it on disk:**

1. **Apple's WAL (Write-Ahead Logging)**: Messages app doesn't immediately write to the main database file. It uses WAL mode where writes are buffered.

2. **Checkpoint Timing**: Apple flushes the WAL to the main database periodically, not immediately.

**Our optimizations to minimize delay:**
- **Fast polling**: Check every 1-2 seconds instead of every 5 seconds
- **Optimized queries**: Minimal database operations for speed
- **Read-only access**: Safe database access that doesn't interfere with Messages.app

**Typical delays you might see:**
- **2-5 seconds**: Normal delay with fast polling (Messages.app running)
- **1-3 seconds**: Faster delay when Messages.app is closed
- **5-10 seconds**: If Apple's Messages app is under heavy load
- **Longer delays**: If your Mac is under high system load

**Safety Notes:**
- We use read-only database access to prevent corruption
- Aggressive WAL checkpointing is disabled to avoid conflicts
- If you see corruption errors, restart Messages.app

### When Polling Starts and Stops

- **NOT automatic**: Polling only runs when YOU start it
- **Manual control**: You decide when to start/stop monitoring
- **State persistence**: Remembers where it left off between sessions

### What Gets Monitored

- **New iMessages**: Detects messages since last check
- **User Resolution**: Automatically creates contact records
- **Text Extraction**: Handles both regular text and binary message data
- **Incremental Only**: Never reprocesses old messages

### Database Impact

- **Read-only**: Never modifies your actual Messages database
- **Safe copying**: Uses Apple's WAL checkpoint system
- **Normalized storage**: Creates clean database structure in `./data/messages.db`

## 🎯 Example Workflows

### For Testing New Messages
```bash
# Run once to see what's new
python scripts/run_polling_service.py poll

# Check status
python scripts/run_polling_service.py status
```

### For Real-time Monitoring
```bash
# Start and leave running
python scripts/run_polling_service.py start --interval 3

# Or use the enhanced UI
python polling_main.py
```

### For Development/Debugging
```bash
# Enable verbose logging
python scripts/run_polling_service.py start --verbose

# Check specific data directory
python scripts/run_polling_service.py status --data-dir ./test_data
```

## 🛡️ Safety Features

- **Non-destructive**: Your original Messages database is never modified
- **Error recovery**: Continues monitoring even if individual polls fail
- **Graceful shutdown**: Press Ctrl+C to stop cleanly
- **State tracking**: Always knows where it left off

## 📊 What You'll See

### Startup
```
🔄 iMessage Polling Service CLI
📁 Data Directory: /Users/nick/Projects/messages-agent/data

🚀 Starting continuous polling...
📱 You'll be notified when new iMessages arrive!
   Press Ctrl+C to stop
```

### During Monitoring
```
📊 Status Update:
   Last ROWID: 15432
   Total Processed: 1,247
   Sync Status: idle
```

### When Messages Arrive
```
🚨 NEW MESSAGES! (2 found, 2 synced)
==================================================
  1. 📥 Handle 5 at 3:15:22 PM
     💬 Meeting moved to 4pm, see you there!
     🆔 ROWID: 15433
```

## 🚫 Stopping the Service

Simply press **Ctrl+C** in the terminal where polling is running:

```
^C
🛑 Received interrupt, stopping...
🏁 Polling service stopped
```

The service will cleanly shut down and remember its position for next time.

## 🔍 Troubleshooting

### No Messages Detected
- Check that you have new messages in your actual Messages app
- Verify the service has permissions to access Messages database
- Try running a single poll first: `python scripts/run_polling_service.py poll`

### Permission Errors
- Ensure Terminal has Full Disk Access in System Preferences > Security & Privacy
- Try running from the correct directory

### Service Won't Start
- Check if database file exists: `python scripts/run_polling_service.py status`
- Verify Python dependencies: `pip install -r requirements.txt`

## ✨ Features Implemented

- ✅ Real-time ROWID-based polling
- ✅ Incremental sync (no reprocessing)
- ✅ User resolution from handle_id
- ✅ Text extraction from binary data
- ✅ Live notifications with message content
- ✅ Configurable polling intervals
- ✅ Status monitoring and error handling
- ✅ Graceful shutdown with state persistence

The polling service is now ready to use! Start with `python scripts/run_polling_service.py start` and watch for new message notifications in real-time.