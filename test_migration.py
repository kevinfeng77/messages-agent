#!/usr/bin/env python3
"""Test script for message migration"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from message_migration import MessageMigration, migrate_database
from logger_config import setup_logging

def test_migration():
    """Test the message migration process"""
    setup_logging()
    
    db_path = Path("data/chat_copy.db")
    
    if not db_path.exists():
        print("Database not found. Please run database manager first.")
        return
    
    print("=== MESSAGE MIGRATION TEST ===")
    
    # Initialize migration
    migration = MessageMigration(db_path)
    
    # Analyze migration scope
    print("\n1. Analyzing migration scope...")
    scope = migration.analyze_migration_scope()
    
    for key, value in scope.items():
        print(f"   {key}: {value}")
    
    # Check if migration is needed
    remaining = scope.get("remaining_to_migrate", 0)
    if remaining == 0:
        print("\n✅ No migration needed - all messages already have text!")
        return
    
    print(f"\n📊 Found {remaining} messages needing migration")
    
    # Create backup
    print("\n2. Creating backup...")
    if migration.create_backup():
        print(f"✅ Backup created: {migration.backup_path}")
    else:
        print("❌ Failed to create backup")
        return
    
    # Add extracted_text column
    print("\n3. Adding extracted_text column...")
    if migration.add_extracted_text_column():
        print("✅ Column added successfully")
    else:
        print("❌ Failed to add column")
        return
    
    # Perform migration (test with small batch first)
    print("\n4. Performing migration (test batch)...")
    results = migration.migrate_messages(batch_size=100, max_batches=5)
    
    if "error" in results:
        print(f"❌ Migration failed: {results['error']}")
        return
    
    print("✅ Migration batch completed:")
    for key, value in results.items():
        print(f"   {key}: {value}")
    
    # Validate migration
    print("\n5. Validating migration...")
    validation = migration.validate_migration()
    
    if "error" in validation:
        print(f"❌ Validation failed: {validation['error']}")
        return
    
    print("✅ Validation completed:")
    for key, value in validation.items():
        print(f"   {key}: {value}")
    
    # Ask user if they want to continue with full migration
    if results.get("total_processed", 0) > 0:
        improvement = validation.get("coverage_improvement_percent", 0)
        print(f"\n🎉 Test migration improved text coverage by {improvement}%!")
        
        response = input("\nDo you want to continue with full migration? (y/n): ")
        if response.lower() == 'y':
            print("\n6. Performing full migration...")
            full_results = migration.migrate_messages(batch_size=1000)
            
            if "error" not in full_results:
                final_validation = migration.validate_migration()
                print("✅ Full migration completed:")
                for key, value in final_validation.items():
                    print(f"   {key}: {value}")
            else:
                print(f"❌ Full migration failed: {full_results['error']}")
        else:
            print("Migration stopped by user")

if __name__ == "__main__":
    test_migration()