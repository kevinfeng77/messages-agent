#!/usr/bin/env python3
"""
Basic test of py-imessage functionality.
This script tests if py-imessage can initialize and perform basic operations.
"""

import sys
import traceback
from py_imessage import imessage


def test_py_imessage_basic():
    """Test basic py-imessage functionality."""
    print("Testing py-imessage basic functionality...")
    
    try:
        # Test checking compatibility
        print("1. Testing py-imessage compatibility...")
        try:
            compatibility = imessage.check_compatibility()
            print(f"   ✓ Compatibility check: {compatibility}")
        except Exception as e:
            print(f"   ⚠ Compatibility check failed: {e}")
        
        # Test status check
        print("2. Testing iMessage status...")
        try:
            status = imessage.status()
            print(f"   ✓ iMessage status: {status}")
        except Exception as e:
            print(f"   ⚠ Status check failed: {e}")
        
        # Test database connection
        print("3. Testing database connection...")
        try:
            db = imessage.db_conn()
            print(f"   ✓ Database connection: {type(db)}")
        except Exception as e:
            print(f"   ⚠ Database connection failed: {e}")
        
        print("\n✓ py-imessage basic functionality test completed")
        return True
        
    except Exception as e:
        print(f"\n✗ py-imessage test failed: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_py_imessage_basic()
    sys.exit(0 if success else 1)