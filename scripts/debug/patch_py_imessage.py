#!/usr/bin/env python3
"""
Patch py-imessage to fix the JavaScript API issue.

This script replaces the broken send_message.js file with a fixed version
that doesn't use the problematic buddies.whose API call.
"""

import shutil
import sys
from pathlib import Path

def find_py_imessage_js():
    """Find the py-imessage JavaScript file location."""
    try:
        import py_imessage
        py_imessage_path = Path(py_imessage.__file__).parent
        js_file = py_imessage_path / "osascript" / "send_message.js"
        
        if js_file.exists():
            return js_file
        else:
            print(f"❌ JavaScript file not found at expected location: {js_file}")
            return None
            
    except ImportError:
        print("❌ py-imessage not installed")
        return None


def backup_original(js_file):
    """Create backup of original JavaScript file."""
    backup_file = js_file.with_suffix('.js.backup')
    
    if not backup_file.exists():
        shutil.copy2(js_file, backup_file)
        print(f"✅ Created backup: {backup_file}")
    else:
        print(f"ℹ️  Backup already exists: {backup_file}")
    
    return backup_file


def apply_patch(js_file):
    """Apply the fixed JavaScript code with improved timing."""
    fixed_js_content = '''const seApp = Application('System Events')
const messagesApp = Application('Messages')
messagesApp.includeStandardAdditions = true;

// Run and get passed in arguments
ObjC.import('stdlib')                               // for exit

var args = $.NSProcessInfo.processInfo.arguments    
var argv = []
var argc = args.count
for (var i = 4; i < argc; i++) {
    // skip 3-word run command at top and this file's name
    argv.push(ObjC.unwrap(args.objectAtIndex(i)))  
}

const number = argv[0]
const message = argv[1]

sendNewMessage(number, message)

function sendNewMessage(number, message) {
    messagesApp.activate()

    // Wait for app to activate
    delay(0.5)
    
    // Create new message
    seApp.keystroke('n', {using: 'command down'})
    
    // Wait for new message window to open
    delay(0.5)
    
    // Type the phone number in To field
    seApp.keystroke(number)
    
    // Wait a bit then press Tab to move to message field
    delay(0.3)
    seApp.keyCode(48) // Tab key to move from To field to message field
    
    // Additional wait to ensure focus is in message field
    delay(0.3)
    
    // Type the message
    seApp.keystroke(message)
    
    // Wait before sending
    delay(0.2)
    
    // Send message (Enter key)
    seApp.keyCode(36)

    // Return a simple success indicator
    return "message_sent_" + Date.now()
}

// Should prevent app from quitting
function quit() {
    return true;
}

seApp.keyUp(59)
$.exit(0)'''

    try:
        js_file.write_text(fixed_js_content)
        print(f"✅ Applied patch to: {js_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to apply patch: {e}")
        return False


def restore_backup(js_file):
    """Restore from backup."""
    backup_file = js_file.with_suffix('.js.backup')
    
    if backup_file.exists():
        shutil.copy2(backup_file, js_file)
        print(f"✅ Restored from backup: {backup_file}")
        return True
    else:
        print(f"❌ No backup found: {backup_file}")
        return False


def main():
    """Main patch function."""
    print("🔧 py-imessage JavaScript API Patcher")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--restore":
        print("🔄 Restoring from backup...")
        js_file = find_py_imessage_js()
        if js_file:
            restore_backup(js_file)
        return
    
    # Find the JavaScript file
    js_file = find_py_imessage_js()
    if not js_file:
        return
    
    print(f"📁 Found py-imessage JavaScript: {js_file}")
    
    # Create backup
    backup_file = backup_original(js_file)
    
    # Apply patch
    if apply_patch(js_file):
        print("\n✅ Patch applied successfully!")
        print("The py-imessage library should now work for sending messages.")
        print(f"To restore original: python {__file__} --restore")
    else:
        print("\n❌ Patch failed!")


if __name__ == "__main__":
    main()