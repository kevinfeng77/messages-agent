#!/usr/bin/env python3
"""Debug script to see what address book data looks like"""

import sys
import sqlite3
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extractors.addressbook_extractor import AddressBookExtractor


def debug_addressbook_data():
    """Show examples of address book records that are failing validation"""
    extractor = AddressBookExtractor()
    databases = extractor._get_addressbook_databases()
    
    if not databases:
        print("No AddressBook databases found")
        return
    
    print("=== AddressBook Data Examples ===\n")
    
    # Look at all databases
    total_first_only = 0
    total_last_only = 0
    
    for db_path in databases:
        print(f"\nExamining database: {db_path}")
        
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                
                # First, show some records with only first name
                print("1. Records with ONLY first name:")
                cursor.execute("""
                    SELECT r.ZFIRSTNAME, r.ZLASTNAME, p.ZFULLNUMBER, e.ZADDRESS
                    FROM ZABCDRECORD r
                    LEFT JOIN ZABCDPHONENUMBER p ON r.Z_PK = p.ZOWNER
                    LEFT JOIN ZABCDEMAILADDRESS e ON r.Z_PK = e.ZOWNER
                    WHERE r.ZFIRSTNAME IS NOT NULL 
                      AND (r.ZLASTNAME IS NULL OR r.ZLASTNAME = '')
                      AND (p.ZFULLNUMBER IS NOT NULL OR e.ZADDRESS IS NOT NULL)
                    LIMIT 5
                """)
                
                for row in cursor.fetchall():
                    first, last, phone, email = row
                    print(f"  First: '{first}', Last: '{last}', Phone: '{phone}', Email: '{email}'")
                
                # Show some records with only last name
                print("\n2. Records with ONLY last name:")
                cursor.execute("""
                    SELECT r.ZFIRSTNAME, r.ZLASTNAME, p.ZFULLNUMBER, e.ZADDRESS
                    FROM ZABCDRECORD r
                    LEFT JOIN ZABCDPHONENUMBER p ON r.Z_PK = p.ZOWNER
                    LEFT JOIN ZABCDEMAILADDRESS e ON r.Z_PK = e.ZOWNER
                    WHERE (r.ZFIRSTNAME IS NULL OR r.ZFIRSTNAME = '')
                      AND r.ZLASTNAME IS NOT NULL
                      AND (p.ZFULLNUMBER IS NOT NULL OR e.ZADDRESS IS NOT NULL)
                    LIMIT 5
                """)
                
                for row in cursor.fetchall():
                    first, last, phone, email = row
                    print(f"  First: '{first}', Last: '{last}', Phone: '{phone}', Email: '{email}'")
                
                # Show counts
                print("\n3. Statistics:")
                
                # Count records with only first name
                cursor.execute("""
                    SELECT COUNT(DISTINCT r.Z_PK)
                    FROM ZABCDRECORD r
                    LEFT JOIN ZABCDPHONENUMBER p ON r.Z_PK = p.ZOWNER
                    LEFT JOIN ZABCDEMAILADDRESS e ON r.Z_PK = e.ZOWNER
                    WHERE r.ZFIRSTNAME IS NOT NULL 
                      AND (r.ZLASTNAME IS NULL OR r.ZLASTNAME = '')
                      AND (p.ZFULLNUMBER IS NOT NULL OR e.ZADDRESS IS NOT NULL)
                """)
                first_only_count = cursor.fetchone()[0]
                
                # Count records with only last name
                cursor.execute("""
                    SELECT COUNT(DISTINCT r.Z_PK)
                    FROM ZABCDRECORD r
                    LEFT JOIN ZABCDPHONENUMBER p ON r.Z_PK = p.ZOWNER
                    LEFT JOIN ZABCDEMAILADDRESS e ON r.Z_PK = e.ZOWNER
                    WHERE (r.ZFIRSTNAME IS NULL OR r.ZFIRSTNAME = '')
                      AND r.ZLASTNAME IS NOT NULL
                      AND (p.ZFULLNUMBER IS NOT NULL OR e.ZADDRESS IS NOT NULL)
                """)
                last_only_count = cursor.fetchone()[0]
                
                # Count records with both names
                cursor.execute("""
                    SELECT COUNT(DISTINCT r.Z_PK)
                    FROM ZABCDRECORD r
                    LEFT JOIN ZABCDPHONENUMBER p ON r.Z_PK = p.ZOWNER
                    LEFT JOIN ZABCDEMAILADDRESS e ON r.Z_PK = e.ZOWNER
                    WHERE r.ZFIRSTNAME IS NOT NULL 
                      AND r.ZLASTNAME IS NOT NULL
                      AND (p.ZFULLNUMBER IS NOT NULL OR e.ZADDRESS IS NOT NULL)
                """)
                both_names_count = cursor.fetchone()[0]
                
                print(f"  Records with only first name: {first_only_count}")
                print(f"  Records with only last name: {last_only_count}")
                print(f"  Records with both names: {both_names_count}")
                
                total_first_only += first_only_count
                total_last_only += last_only_count
                
                print("-" * 50)
                
        except sqlite3.Error as e:
            print(f"Error reading database: {e}")
    
    print(f"\nTOTAL across all databases:")
    print(f"  Records with only first name: {total_first_only}")
    print(f"  Records with only last name: {total_last_only}")
    print(f"  Total problematic records: {total_first_only + total_last_only}")


if __name__ == "__main__":
    debug_addressbook_data()