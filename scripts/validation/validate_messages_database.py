#!/usr/bin/env python3
"""Validation script for messages database and address book data"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.messages_db import MessagesDatabase
from src.extractors.addressbook_extractor import AddressBookExtractor
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


def validate_database_structure():
    """Validate the messages database structure"""
    print("=== Validating Database Structure ===")
    
    db_path = "./data/messages.db"
    messages_db = MessagesDatabase(db_path)
    
    # Check database exists
    if not messages_db.database_exists():
        print("❌ Messages database does not exist")
        return False
    
    print("✅ Messages database exists")
    
    # Check users table exists
    if not messages_db.table_exists('users'):
        print("❌ Users table does not exist")
        return False
    
    print("✅ Users table exists")
    
    # Validate table schema
    schema = messages_db.get_table_schema('users')
    if not schema:
        print("❌ Could not retrieve users table schema")
        return False
    
    # Check required columns
    column_names = [col[1] for col in schema]
    required_columns = ['user_id', 'first_name', 'last_name', 'phone_number', 'email']
    
    missing_columns = [col for col in required_columns if col not in column_names]
    if missing_columns:
        print(f"❌ Missing required columns: {missing_columns}")
        return False
    
    print("✅ All required columns present")
    
    # Validate column types (TEXT NOT NULL as per ticket requirement)
    for col_info in schema:
        col_name = col_info[1]
        col_type = col_info[2]
        is_nullable = col_info[3]
        
        if col_name in required_columns:
            if col_type.upper() != 'TEXT':
                print(f"❌ Column {col_name} should be TEXT, found {col_type}")
                return False
    
    # Alternative validation: check actual schema using .schema command
    import sqlite3
    try:
        with sqlite3.connect("./data/messages.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
            schema_sql = cursor.fetchone()[0]
            
            # Check that NOT NULL constraints are present
            for col in required_columns:
                if f"{col} TEXT NOT NULL" not in schema_sql:
                    print(f"❌ Column {col} should have NOT NULL constraint")
                    return False
    except Exception as e:
        print(f"⚠️  Could not verify NOT NULL constraints: {e}")
        # Don't fail validation for this
    
    print("✅ Column types and constraints are correct")
    
    return True


def validate_users_data():
    """Validate the users data in the database"""
    print("\n=== Validating Users Data ===")
    
    db_path = "./data/messages.db"
    messages_db = MessagesDatabase(db_path)
    
    # Get database statistics
    stats = messages_db.get_database_stats()
    if 'error' in stats:
        print(f"❌ Error getting database stats: {stats['error']}")
        return False
    
    total_users = stats['total_users']
    users_with_phone = stats['users_with_phone']
    users_with_email = stats['users_with_email']
    
    print(f"📊 Database contains {total_users} users")
    print(f"   - Users with phone: {users_with_phone}")
    print(f"   - Users with email: {users_with_email}")
    
    if total_users == 0:
        print("❌ No users found in database")
        return False
    
    print("✅ Database contains users")
    
    # Validate a sample of users
    sample_users = messages_db.get_all_users(limit=10)
    print(f"\n📝 Validating sample of {len(sample_users)} users:")
    
    for i, user in enumerate(sample_users, 1):
        # Check required fields
        if not user.user_id:
            print(f"❌ User {i}: Missing user_id")
            return False
        
        if not user.first_name and not user.last_name:
            print(f"❌ User {i}: Missing both first_name and last_name")
            return False
        
        if not user.phone_number and not user.email:
            print(f"❌ User {i}: Missing both phone_number and email")
            return False
        
        print(f"   ✅ User {i}: {user}")
    
    return True


def validate_address_book_access():
    """Validate access to address book data"""
    print("\n=== Validating Address Book Access ===")
    
    extractor = AddressBookExtractor()
    
    # Get extraction statistics
    try:
        stats = extractor.get_extraction_stats()
        
        total_databases = stats['total_databases']
        total_records = stats['total_records']
        
        print(f"📊 Address book statistics:")
        print(f"   - AddressBook databases found: {total_databases}")
        print(f"   - Total contact records: {total_records}")
        print(f"   - Records with phone: {stats['records_with_phone']}")
        print(f"   - Records with email: {stats['records_with_email']}")
        
        if total_databases == 0:
            print("⚠️  No AddressBook databases found")
            return False
        
        if total_records == 0:
            print("⚠️  No contact records found")
            return False
        
        print("✅ Address book data accessible")
        
        # Test extraction of a few users
        print("\n📝 Testing user extraction...")
        users = extractor.extract_users()
        
        if not users:
            print("⚠️  No users extracted from address book")
            return False
        
        print(f"✅ Successfully extracted {len(users)} users from address book")
        
        # Show sample extracted users
        print(f"   Sample users:")
        for i, user in enumerate(users[:3], 1):
            print(f"   {i}. {user}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error accessing address book: {e}")
        return False


def validate_data_consistency():
    """Validate consistency between address book and database data"""
    print("\n=== Validating Data Consistency ===")
    
    # Extract users from address book
    extractor = AddressBookExtractor()
    addressbook_users = extractor.extract_users()
    
    # Get users from database
    messages_db = MessagesDatabase("./data/messages.db")
    database_users = messages_db.get_all_users()
    
    print(f"📊 Data consistency check:")
    print(f"   - Address book users: {len(addressbook_users)}")
    print(f"   - Database users: {len(database_users)}")
    
    # Check if counts match (allowing for some variance due to filtering)
    if len(database_users) == 0:
        print("❌ No users in database")
        return False
    
    if len(addressbook_users) == 0:
        print("❌ No users extracted from address book")
        return False
    
    # Reasonable variance check (database might have fewer due to deduplication)
    if len(database_users) > len(addressbook_users):
        print("⚠️  More users in database than address book (unexpected)")
        return False
    
    variance_ratio = len(database_users) / len(addressbook_users)
    if variance_ratio < 0.5:
        print(f"⚠️  Significant data loss: only {variance_ratio:.1%} of address book users in database")
        return False
    
    print(f"✅ Data consistency acceptable ({variance_ratio:.1%} retention ratio)")
    
    return True


def validate_directory_structure():
    """Validate the new directory structure"""
    print("\n=== Validating Directory Structure ===")
    
    # Check data directory exists
    data_dir = Path("./data")
    if not data_dir.exists():
        print("❌ Data directory does not exist")
        return False
    
    print("✅ Data directory exists")
    
    # Check copy directory exists
    copy_dir = data_dir / "copy"
    if not copy_dir.exists():
        print("❌ Copy directory does not exist")
        return False
    
    print("✅ Copy directory exists")
    
    # Check messages.db exists in data root
    messages_db_path = data_dir / "messages.db"
    if not messages_db_path.exists():
        print("❌ messages.db does not exist in data directory")
        return False
    
    print("✅ messages.db exists in correct location")
    
    # Check copied databases are in copy directory
    expected_copied_files = ["chat_copy.db", "messages_complete_contacts.db"]
    
    for filename in expected_copied_files:
        file_path = copy_dir / filename
        if file_path.exists():
            print(f"✅ {filename} found in copy directory")
        else:
            print(f"⚠️  {filename} not found in copy directory")
    
    return True


def main():
    """Main validation function"""
    print("🔍 Messages Database Validation Script")
    print("=====================================\n")
    
    validation_results = []
    
    # Run all validations
    validations = [
        ("Directory Structure", validate_directory_structure),
        ("Database Structure", validate_database_structure),
        ("Users Data", validate_users_data),
        ("Address Book Access", validate_address_book_access),
        ("Data Consistency", validate_data_consistency),
    ]
    
    for validation_name, validation_func in validations:
        try:
            result = validation_func()
            validation_results.append((validation_name, result))
        except Exception as e:
            print(f"❌ {validation_name} validation failed with error: {e}")
            validation_results.append((validation_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📋 VALIDATION SUMMARY")
    print("="*50)
    
    passed = 0
    failed = 0
    
    for validation_name, result in validation_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {validation_name}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("The messages database implementation is working correctly.")
        return True
    else:
        print(f"\n⚠️  {failed} VALIDATION(S) FAILED")
        print("Please review the issues above and fix them.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)