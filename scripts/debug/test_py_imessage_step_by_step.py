#!/usr/bin/env python3
"""
Step-by-step debugging of py-imessage send process.
"""

import os
import subprocess
import sys
from pathlib import Path
from shlex import quote

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_javascript_directly():
    """Test JavaScript directly."""
    print("🔧 Testing JavaScript directly")
    print("=" * 40)
    
    import py_imessage
    py_imessage_path = Path(py_imessage.__file__).parent
    js_path = py_imessage_path / "osascript" / "send_message.js"
    
    print(f"JavaScript path: {js_path}")
    
    test_number = "+12538861994"
    test_message = "Direct JS test"
    
    cmd = f'osascript -l JavaScript {js_path} {quote(test_number)} {quote(test_message)}'
    print(f"Command: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"Return code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        if result.returncode == 0:
            print("✅ JavaScript execution successful")
            return True
        else:
            print("❌ JavaScript execution failed")
            return False
            
    except Exception as e:
        print(f"❌ Error running JavaScript: {e}")
        return False


def test_py_imessage_subprocess():
    """Test py-imessage subprocess call manually."""
    print("\n📞 Testing py-imessage subprocess manually")
    print("=" * 40)
    
    try:
        import py_imessage
        py_imessage_path = Path(py_imessage.__file__).parent
        js_path = py_imessage_path / "osascript" / "send_message.js"
        
        test_number = "+12538861994"
        test_message = "Manual subprocess test"
        
        # Replicate exact py-imessage logic
        cmd = f'osascript -l JavaScript {js_path} {quote(test_number)} {quote(test_message)}'
        print(f"Command: {cmd}")
        
        # Use subprocess.call like py-imessage does
        print("Calling subprocess.call()...")
        return_code = subprocess.call(cmd, shell=True)
        print(f"Return code: {return_code}")
        
        if return_code == 0:
            print("✅ Subprocess call successful")
            return True
        else:
            print("❌ Subprocess call failed")
            return False
            
    except Exception as e:
        print(f"❌ Error in subprocess test: {e}")
        return False


def test_database_operations():
    """Test database operations that py-imessage does after sending."""
    print("\n💾 Testing database operations")
    print("=" * 40)
    
    try:
        from py_imessage import db_conn
        
        print("Opening database connection...")
        db_conn.open()
        print("✅ Database opened")
        
        print("Getting most recently sent text...")
        try:
            guid = db_conn.get_most_recently_sent_text()
            print(f"✅ Most recent GUID: {guid}")
        except Exception as e:
            print(f"❌ Error getting recent text: {e}")
            if "authorization denied" in str(e).lower():
                print("💡 This is the database access issue!")
            return False
        
        print("Cleaning up database...")
        db_conn.clean_up()
        print("✅ Database cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Database operations failed: {e}")
        return False


def test_full_py_imessage_flow():
    """Test the complete py-imessage flow step by step."""
    print("\n🔄 Testing complete py-imessage flow")
    print("=" * 40)
    
    test_number = "+12538861994"
    test_message = "Complete flow test"
    
    try:
        import py_imessage
        from py_imessage import db_conn
        from time import sleep
        
        # Step 1: Build command (like py-imessage does)
        py_imessage_path = Path(py_imessage.__file__).parent
        js_path = py_imessage_path / "osascript" / "send_message.js"
        cmd = f'osascript -l JavaScript {js_path} {quote(test_number)} {quote(test_message)}'
        
        print(f"Step 1 - Command: {cmd}")
        
        # Step 2: Execute JavaScript (like py-imessage does)
        print("Step 2 - Executing JavaScript...")
        return_code = subprocess.call(cmd, shell=True)
        print(f"JavaScript return code: {return_code}")
        
        if return_code != 0:
            print("❌ JavaScript execution failed")
            return False
        
        # Step 3: Open database (like py-imessage does)
        print("Step 3 - Opening database...")
        db_conn.open()
        
        # Step 4: Sleep (like py-imessage does)
        print("Step 4 - Sleeping for 1 second...")
        sleep(1)
        
        # Step 5: Get GUID (like py-imessage does)
        print("Step 5 - Getting message GUID...")
        guid = db_conn.get_most_recently_sent_text()
        print(f"✅ Complete flow successful! GUID: {guid}")
        
        return guid
        
    except Exception as e:
        print(f"❌ Complete flow failed: {e}")
        return False


def main():
    """Run step-by-step py-imessage debugging."""
    print("🐛 py-imessage Step-by-Step Debug")
    print("=" * 50)
    print()
    
    # Test each component separately
    js_ok = test_javascript_directly()
    subprocess_ok = test_py_imessage_subprocess()
    db_ok = test_database_operations()
    
    if js_ok and subprocess_ok and not db_ok:
        print("\n💡 Analysis:")
        print("• JavaScript sending works fine")
        print("• Subprocess execution works fine") 
        print("• Database access is the problem")
        print("\nSolution: Grant 'Full Disk Access' to Terminal in System Preferences")
        print("This will allow py-imessage to read the Messages database")
    elif js_ok and subprocess_ok and db_ok:
        print("\n🎉 All components work individually!")
        print("Let's test the complete flow...")
        
        guid = test_full_py_imessage_flow()
        if guid:
            print(f"\n✅ py-imessage is fully functional! Last message GUID: {guid}")
        else:
            print(f"\n❌ Complete flow failed despite individual components working")
    else:
        print(f"\n❌ Multiple issues detected:")
        print(f"  JavaScript: {'✅' if js_ok else '❌'}")
        print(f"  Subprocess: {'✅' if subprocess_ok else '❌'}")
        print(f"  Database: {'✅' if db_ok else '❌'}")


if __name__ == "__main__":
    main()