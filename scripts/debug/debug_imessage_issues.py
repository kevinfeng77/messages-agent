#!/usr/bin/env python3
"""
Debug script for diagnosing py-imessage issues.

This script helps identify and resolve common py-imessage problems:
1. JavaScript API compatibility issues
2. Database access permissions
3. Messages app configuration
4. System requirements
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import py_imessage.imessage as py_imessage_lib
    IMESSAGE_AVAILABLE = True
except ImportError as e:
    py_imessage_lib = None
    IMESSAGE_AVAILABLE = False
    import_error = e


def check_system_requirements():
    """Check if system meets py-imessage requirements."""
    print("🔍 System Requirements Check")
    print("=" * 40)
    
    # Check macOS
    try:
        result = subprocess.run(['sw_vers'], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if 'ProductName' in line or 'ProductVersion' in line:
                    print(f"✅ {line}")
        else:
            print("❌ Not running on macOS")
            return False
    except FileNotFoundError:
        print("❌ Not running on macOS (sw_vers not found)")
        return False
    
    # Check Messages app
    messages_app_path = "/Applications/Messages.app"
    if os.path.exists(messages_app_path):
        print(f"✅ Messages app found at {messages_app_path}")
    else:
        print(f"❌ Messages app not found at {messages_app_path}")
        return False
    
    return True


def check_imessage_library():
    """Check py-imessage library status."""
    print("\n📚 py-imessage Library Check")
    print("=" * 40)
    
    if not IMESSAGE_AVAILABLE:
        print(f"❌ py-imessage not available: {import_error}")
        print("\nTo install: pip install py-imessage")
        return False
    
    print("✅ py-imessage library imported successfully")
    
    # Check available functions
    try:
        send_func = getattr(py_imessage_lib, 'send', None)
        if send_func:
            print("✅ send() function available")
        else:
            print("❌ send() function not found")
            
        # Check for other expected functions
        for func_name in ['recent', 'get_recent']:
            if hasattr(py_imessage_lib, func_name):
                print(f"✅ {func_name}() function available")
            else:
                print(f"⚠️  {func_name}() function not found")
                
    except Exception as e:
        print(f"❌ Error checking library functions: {e}")
        return False
    
    return True


def check_messages_database():
    """Check Messages database accessibility."""
    print("\n💾 Messages Database Check")
    print("=" * 40)
    
    # Common paths for Messages database
    home = Path.home()
    db_paths = [
        home / "Library" / "Messages" / "chat.db",
        home / "Library" / "Messages" / "chat.db-wal",
        home / "Library" / "Messages" / "chat.db-shm"
    ]
    
    main_db = db_paths[0]
    
    # Check if database file exists
    if not main_db.exists():
        print(f"❌ Messages database not found at {main_db}")
        print("   This usually means Messages has never been used on this system")
        return False
    
    print(f"✅ Messages database found at {main_db}")
    
    # Check file permissions
    if os.access(main_db, os.R_OK):
        print("✅ Database is readable")
    else:
        print("❌ Database is not readable")
        print("   Solution: Grant 'Full Disk Access' to Terminal/Python in System Preferences > Security & Privacy")
        return False
    
    # Try to open database
    try:
        conn = sqlite3.connect(str(main_db))
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT COUNT(*) FROM chat")
        chat_count = cursor.fetchone()[0]
        print(f"✅ Database accessible - found {chat_count} chats")
        
        # Check for handle table
        cursor.execute("SELECT COUNT(*) FROM handle")
        handle_count = cursor.fetchone()[0]
        print(f"✅ Found {handle_count} contact handles")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database access error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected database error: {e}")
        return False


def check_messages_app_status():
    """Check if Messages app is properly configured."""
    print("\n📱 Messages App Configuration Check")
    print("=" * 40)
    
    # Check if Messages is running
    try:
        result = subprocess.run(['pgrep', 'Messages'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Messages app is running")
        else:
            print("⚠️  Messages app is not running")
            print("   Consider starting Messages app before sending messages")
    except Exception as e:
        print(f"❌ Error checking Messages app status: {e}")
    
    # Check for iMessage sign-in (indirect check via database)
    try:
        home = Path.home()
        db_path = home / "Library" / "Messages" / "chat.db"
        
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Check for any recent activity (messages in last 30 days)
            cursor.execute("""
                SELECT COUNT(*) FROM message 
                WHERE date > (strftime('%s', 'now') - 2592000) * 1000000000
            """)
            recent_count = cursor.fetchone()[0]
            
            if recent_count > 0:
                print(f"✅ Recent message activity detected ({recent_count} messages)")
            else:
                print("⚠️  No recent message activity")
                print("   This might indicate iMessage is not properly configured")
            
            conn.close()
            
    except Exception as e:
        print(f"⚠️  Could not check message activity: {e}")


def check_javascript_api():
    """Test the JavaScript API that py-imessage uses."""
    print("\n🔧 JavaScript API Test")
    print("=" * 40)
    
    # The problematic JavaScript code from the error
    test_script = """
    try {
        const messagesApp = Application('Messages');
        console.log('Messages app accessible:', typeof messagesApp);
        console.log('buddies property:', typeof messagesApp.buddies);
        console.log('whose method:', typeof messagesApp.buddies.whose);
    } catch (error) {
        console.log('Error:', error.message);
    }
    """
    
    try:
        # Write test script to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(test_script)
            temp_script = f.name
        
        # Run osascript with JavaScript
        result = subprocess.run(
            ['osascript', '-l', 'JavaScript', temp_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Clean up temp file
        os.unlink(temp_script)
        
        if result.returncode == 0:
            print("✅ JavaScript API test completed:")
            print(result.stdout)
        else:
            print("❌ JavaScript API test failed:")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("❌ JavaScript API test timed out")
    except Exception as e:
        print(f"❌ Error running JavaScript API test: {e}")


def suggest_solutions():
    """Provide solutions for common issues."""
    print("\n💡 Suggested Solutions")
    print("=" * 40)
    
    print("1. **Grant Full Disk Access to Terminal/Python:**")
    print("   • System Preferences > Security & Privacy > Privacy > Full Disk Access")
    print("   • Add Terminal.app and/or Python executable")
    print("   • Restart Terminal after granting permissions")
    print()
    
    print("2. **Ensure Messages App is Configured:**")
    print("   • Open Messages app")
    print("   • Sign in with your Apple ID")
    print("   • Enable iMessage in Messages > Preferences")
    print("   • Send at least one manual message to verify it works")
    print()
    
    print("3. **Alternative: Use AppleScript Instead:**")
    print("   • py-imessage relies on JavaScript for Automation")
    print("   • Consider using direct AppleScript for better compatibility")
    print("   • AppleScript is more stable across macOS versions")
    print()
    
    print("4. **Test with Simple AppleScript:**")
    print('   osascript -e \'tell application "Messages" to send "test" to buddy "+1234567890"\'')
    print()
    
    print("5. **Check macOS Compatibility:**")
    print("   • py-imessage may not support the latest macOS versions")
    print("   • Consider downgrading or finding alternatives")


def main():
    """Run comprehensive diagnostic checks."""
    print("🔧 py-imessage Diagnostic Tool")
    print("=" * 50)
    print()
    
    all_good = True
    
    # Run all checks
    all_good &= check_system_requirements()
    all_good &= check_imessage_library()
    all_good &= check_messages_database()
    check_messages_app_status()
    check_javascript_api()
    
    print("\n" + "=" * 50)
    
    if all_good:
        print("✅ All critical checks passed!")
        print("If you're still having issues, the problem might be:")
        print("• JavaScript API compatibility with your macOS version")
        print("• Messages app permissions or configuration")
    else:
        print("❌ Some issues were found. See solutions below.")
    
    suggest_solutions()


if __name__ == "__main__":
    main()