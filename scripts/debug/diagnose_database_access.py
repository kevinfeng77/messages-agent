#!/usr/bin/env python3
"""
Diagnose py-imessage database access issues.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def check_messages_database_direct():
    """Check direct access to Messages database."""
    print("🔍 Direct Messages Database Access Test")
    print("=" * 40)
    
    home = Path.home()
    db_path = home / "Library" / "Messages" / "chat.db"
    
    print(f"Database path: {db_path}")
    
    # Check if file exists
    if not db_path.exists():
        print("❌ Messages database not found")
        return False
    
    print("✅ Database file exists")
    
    # Check file permissions
    try:
        stat_info = db_path.stat()
        print(f"✅ File permissions: {oct(stat_info.st_mode)}")
        print(f"✅ File owner: {stat_info.st_uid}")
        print(f"✅ Current user: {os.getuid()}")
    except Exception as e:
        print(f"❌ Error getting file stats: {e}")
    
    # Test read access
    if os.access(db_path, os.R_OK):
        print("✅ File is readable by current user")
    else:
        print("❌ File is NOT readable by current user")
        return False
    
    # Test database connection
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT COUNT(*) FROM chat")
        chat_count = cursor.fetchone()[0]
        print(f"✅ Database accessible - {chat_count} chats found")
        
        # Test message count
        cursor.execute("SELECT COUNT(*) FROM message")
        message_count = cursor.fetchone()[0]
        print(f"✅ Found {message_count} messages in database")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_py_imessage_recent():
    """Test py-imessage recent message reading."""
    print("\n📖 py-imessage Recent Messages Test")
    print("=" * 40)
    
    try:
        import py_imessage.imessage as py_imessage_lib
        print("✅ py-imessage imported")
    except ImportError as e:
        print(f"❌ py-imessage import failed: {e}")
        return False
    
    # Test if py-imessage has reading functions
    if hasattr(py_imessage_lib, 'recent'):
        print("✅ py-imessage.recent() function available")
        try:
            messages = py_imessage_lib.recent(limit=5)
            print(f"✅ Retrieved {len(messages)} recent messages")
            return True
        except Exception as e:
            print(f"❌ py-imessage.recent() failed: {e}")
            if "authorization denied" in str(e).lower():
                print("💡 This is the database permission issue")
            return False
    else:
        print("⚠️  py-imessage.recent() not available")
        
        # Check for other reading functions
        available_funcs = [name for name in dir(py_imessage_lib) 
                          if not name.startswith('_') and callable(getattr(py_imessage_lib, name))]
        print(f"Available functions: {available_funcs}")
        return False


def check_terminal_permissions():
    """Check Terminal permissions for database access."""
    print("\n🔑 Terminal Database Permissions Check")
    print("=" * 40)
    
    # Check if running from Terminal vs other app
    parent_process = os.getppid()
    try:
        result = subprocess.run(['ps', '-p', str(parent_process), '-o', 'comm='], 
                              capture_output=True, text=True)
        parent_name = result.stdout.strip()
        print(f"Parent process: {parent_name}")
        
        if 'Terminal' in parent_name:
            print("✅ Running from Terminal app")
        elif 'Code' in parent_name or 'code' in parent_name:
            print("✅ Running from VS Code")
        else:
            print(f"ℹ️  Running from: {parent_name}")
            
    except Exception as e:
        print(f"⚠️  Could not determine parent process: {e}")


def suggest_solutions():
    """Suggest solutions for database access issues."""
    print("\n💡 Database Access Solutions")
    print("=" * 40)
    
    print("1. **Grant Full Disk Access:**")
    print("   • System Preferences > Security & Privacy > Privacy")
    print("   • Select 'Full Disk Access' in left sidebar")
    print("   • Click '+' and add Terminal.app")
    print("   • If using VS Code, also add 'Visual Studio Code.app'")
    print("   • Restart the application after granting access")
    print()
    
    print("2. **Alternative: Use AppleScript for reading too:**")
    print("   • AppleScript can read message history without database access")
    print("   • More reliable across macOS versions")
    print("   • Doesn't require Full Disk Access")
    print()
    
    print("3. **Test with different applications:**")
    print("   • Try running from Terminal.app directly")
    print("   • Try from a different Python IDE")
    print("   • Some apps have better sandboxing permissions")


def main():
    """Run all database diagnostics."""
    print("🧪 py-imessage Database Access Diagnostics")
    print("=" * 50)
    print()
    
    # Run diagnostic tests
    db_direct_ok = check_messages_database_direct()
    py_imessage_ok = test_py_imessage_recent()
    check_terminal_permissions()
    
    print("\n" + "=" * 50)
    
    if db_direct_ok and py_imessage_ok:
        print("✅ All database access tests passed!")
        print("py-imessage should work for both sending and reading.")
    elif db_direct_ok and not py_imessage_ok:
        print("⚠️  Direct database access works, but py-imessage fails")
        print("This suggests py-imessage has additional permission requirements.")
    else:
        print("❌ Database access issues detected")
        print("Full Disk Access permissions likely needed.")
    
    suggest_solutions()


if __name__ == "__main__":
    main()