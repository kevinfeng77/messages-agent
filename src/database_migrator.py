#!/usr/bin/env python3
"""Database Migration Script - Creates joined messages/contacts database"""

import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.logger_config import get_logger

logger = get_logger(__name__)


class DatabaseMigrator:
    """Handles migration from Messages DB to custom joined format"""

    def __init__(
        self,
        source_db_path,
        target_db_path,
        contacts_db_path=None,
        addressbook_db_path=None,
    ):
        self.source_db_path = source_db_path
        self.target_db_path = target_db_path
        self.contacts_db_path = (
            contacts_db_path
            or "/Users/{}/Library/Contacts/accounts.accountdb".format(
                os.getenv("USER", "")
            )
        )
        # Default to iCloud AddressBook database
        self.addressbook_db_path = (
            addressbook_db_path
            or "/Users/{}/Library/Application Support/AddressBook/Sources/0E9330B9-85E5-48C9-ACF9-4EE9217D8F4A/AddressBook-v22.abcddb".format(
                os.getenv("USER", "")
            )
        )

    def create_target_schema(self):
        """Create the new database schema"""
        logger.info(f"Creating target database schema at {self.target_db_path}")

        with sqlite3.connect(self.target_db_path) as conn:
            cursor = conn.cursor()

            # Drop table if exists
            cursor.execute("DROP TABLE IF EXISTS messages_with_contacts")

            # Create new schema
            cursor.execute(
                """
                CREATE TABLE messages_with_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    
                    -- Message data
                    message_id INTEGER NOT NULL,
                    guid TEXT,
                    text TEXT,
                    date INTEGER,
                    date_read INTEGER,
                    date_delivered INTEGER,
                    is_from_me INTEGER DEFAULT 0,
                    is_read INTEGER DEFAULT 0,
                    is_delivered INTEGER DEFAULT 0,
                    is_sent INTEGER DEFAULT 0,
                    service TEXT,
                    account TEXT,
                    error INTEGER DEFAULT 0,
                    
                    -- Handle/Contact data
                    handle_id INTEGER,
                    contact_id TEXT,
                    phone_email TEXT,
                    country TEXT,
                    service_type TEXT,
                    
                    -- Contact information
                    contact_first_name TEXT,
                    contact_last_name TEXT,
                    contact_full_name TEXT,
                    
                    -- Account mapping (for future use)
                    account_type TEXT,
                    account_display_name TEXT,
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes for performance
            cursor.execute(
                "CREATE INDEX idx_message_id ON messages_with_contacts(message_id)"
            )
            cursor.execute(
                "CREATE INDEX idx_handle_id ON messages_with_contacts(handle_id)"
            )
            cursor.execute("CREATE INDEX idx_date ON messages_with_contacts(date)")
            cursor.execute(
                "CREATE INDEX idx_phone_email ON messages_with_contacts(phone_email)"
            )
            cursor.execute(
                "CREATE INDEX idx_is_from_me ON messages_with_contacts(is_from_me)"
            )
            cursor.execute(
                "CREATE INDEX idx_contact_name ON messages_with_contacts(contact_full_name)"
            )

            conn.commit()
            logger.info("Target database schema created successfully")

    def migrate_data(self, limit=None):
        """Migrate data from source to target database"""
        logger.info("Starting data migration...")

        # Verify source database exists
        if not os.path.exists(self.source_db_path):
            raise FileNotFoundError(f"Source database not found: {self.source_db_path}")

        # Build contact lookup from AddressBook
        contact_lookup = self._build_contact_lookup()

        with sqlite3.connect(self.source_db_path) as source_conn:
            with sqlite3.connect(self.target_db_path) as target_conn:
                source_cursor = source_conn.cursor()
                target_cursor = target_conn.cursor()

                # Build the query with optional limit
                query = """
                    SELECT 
                        m.ROWID as message_id,
                        m.guid,
                        m.text,
                        m.date,
                        m.date_read,
                        m.date_delivered,
                        m.is_from_me,
                        m.is_read,
                        m.is_delivered,
                        m.is_sent,
                        m.service,
                        m.account,
                        m.error,
                        m.handle_id,
                        h.id as contact_id,
                        h.id as phone_email,
                        h.country,
                        h.service as service_type
                    FROM message m
                    LEFT JOIN handle h ON m.handle_id = h.ROWID
                    ORDER BY m.date DESC
                """

                if limit:
                    query += f" LIMIT {limit}"

                logger.info(
                    f"Executing migration query{'with limit ' + str(limit) if limit else ''}..."
                )
                source_cursor.execute(query)

                # Prepare insert statement
                insert_sql = """
                    INSERT INTO messages_with_contacts (
                        message_id, guid, text, date, date_read, date_delivered,
                        is_from_me, is_read, is_delivered, is_sent, service, account, error,
                        handle_id, contact_id, phone_email, country, service_type,
                        contact_first_name, contact_last_name, contact_full_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                # Batch insert for performance
                batch_size = 1000
                batch = []
                total_migrated = 0

                for row in source_cursor:
                    # Look up contact info
                    phone_email = row[15]  # phone_email field
                    contact_info = self._lookup_contact(phone_email, contact_lookup)

                    # Add contact fields to row
                    enhanced_row = list(row) + [
                        contact_info["first_name"],
                        contact_info["last_name"],
                        contact_info["full_name"],
                    ]

                    batch.append(enhanced_row)

                    if len(batch) >= batch_size:
                        target_cursor.executemany(insert_sql, batch)
                        total_migrated += len(batch)
                        logger.info(f"Migrated {total_migrated} messages...")
                        batch = []

                # Insert remaining batch
                if batch:
                    target_cursor.executemany(insert_sql, batch)
                    total_migrated += len(batch)

                target_conn.commit()
                logger.info(f"Migration completed: {total_migrated} messages migrated")

                return total_migrated

    def _build_contact_lookup(self):
        """Build a lookup dictionary for phone/email to contact names"""
        logger.info("Building contact lookup from all AddressBook sources...")
        contact_lookup = {}

        # Get all AddressBook source directories
        addressbook_root = (
            f"/Users/{os.getenv('USER', '')}/Library/Application Support/AddressBook"
        )
        sources_dir = os.path.join(addressbook_root, "Sources")

        source_databases = []

        # Add main database if it exists
        main_db = os.path.join(addressbook_root, "AddressBook-v22.abcddb")
        if os.path.exists(main_db):
            source_databases.append(main_db)

        # Add all source databases
        if os.path.exists(sources_dir):
            for source_dir in os.listdir(sources_dir):
                source_path = os.path.join(
                    sources_dir, source_dir, "AddressBook-v22.abcddb"
                )
                if os.path.exists(source_path):
                    source_databases.append(source_path)

        logger.info(f"Found {len(source_databases)} AddressBook databases to process")

        for db_path in source_databases:
            try:
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()

                    # Get phone number to contact mapping
                    cursor.execute(
                        """
                        SELECT p.ZFULLNUMBER, r.ZFIRSTNAME, r.ZLASTNAME
                        FROM ZABCDPHONENUMBER p 
                        JOIN ZABCDRECORD r ON p.ZOWNER = r.Z_PK
                        WHERE p.ZFULLNUMBER IS NOT NULL
                    """
                    )

                    phone_count = 0
                    for row in cursor.fetchall():
                        phone, first, last = row
                        normalized_phone = self._normalize_phone(phone)
                        if normalized_phone:  # Only add if normalization succeeds
                            contact_lookup[normalized_phone] = {
                                "first_name": first,
                                "last_name": last,
                                "full_name": self._format_full_name(first, last),
                            }
                            phone_count += 1

                    # Get email to contact mapping
                    cursor.execute(
                        """
                        SELECT e.ZADDRESS, r.ZFIRSTNAME, r.ZLASTNAME
                        FROM ZABCDEMAILADDRESS e 
                        JOIN ZABCDRECORD r ON e.ZOWNER = r.Z_PK
                        WHERE e.ZADDRESS IS NOT NULL
                    """
                    )

                    email_count = 0
                    for row in cursor.fetchall():
                        email, first, last = row
                        if email:
                            contact_lookup[email.lower()] = {
                                "first_name": first,
                                "last_name": last,
                                "full_name": self._format_full_name(first, last),
                            }
                            email_count += 1

                    logger.info(
                        f"Database {os.path.basename(os.path.dirname(db_path))}: {phone_count} phones, {email_count} emails"
                    )

            except Exception as e:
                logger.error(f"Error processing database {db_path}: {e}")

        logger.info(f"Built contact lookup with {len(contact_lookup)} total entries")
        return contact_lookup

    def _normalize_phone(self, phone):
        """Normalize phone number for lookup"""
        if not phone:
            return ""
        # Remove all non-digits
        normalized = "".join(filter(str.isdigit, phone))
        # If it starts with 1, remove it (US country code)
        if normalized.startswith("1") and len(normalized) == 11:
            normalized = normalized[1:]
        return normalized

    def _format_full_name(self, first, last):
        """Format full name from first and last"""
        if first and last:
            return f"{first} {last}"
        elif first:
            return first
        elif last:
            return last
        else:
            return None

    def _lookup_contact(self, phone_email, contact_lookup):
        """Look up contact info for a phone/email"""
        if not phone_email:
            return {"first_name": None, "last_name": None, "full_name": None}

        # Try direct lookup first
        if phone_email in contact_lookup:
            return contact_lookup[phone_email]

        # Try normalized phone lookup
        if phone_email.startswith("+") or any(c.isdigit() for c in phone_email):
            normalized = self._normalize_phone(phone_email)
            if normalized in contact_lookup:
                return contact_lookup[normalized]

        # Try email lookup
        email_key = phone_email.lower()
        if email_key in contact_lookup:
            return contact_lookup[email_key]

        # No match found
        return {"first_name": None, "last_name": None, "full_name": None}

    def add_account_mapping(self):
        """Add account information from contacts database (future enhancement)"""
        if not os.path.exists(self.contacts_db_path):
            logger.warning(f"Contacts database not found: {self.contacts_db_path}")
            return

        logger.info("Adding account mapping...")

        try:
            with sqlite3.connect(self.contacts_db_path) as contacts_conn:
                with sqlite3.connect(self.target_db_path) as target_conn:
                    contacts_cursor = contacts_conn.cursor()
                    target_cursor = target_conn.cursor()

                    # Get account information
                    contacts_cursor.execute(
                        """
                        SELECT ZACCOUNTTYPE, ZDISPLAYNAME, ZEXTERNALIDENTIFIER
                        FROM ZACCOUNTMODEL
                    """
                    )

                    accounts = contacts_cursor.fetchall()
                    logger.info(f"Found {len(accounts)} accounts in contacts database")

                    # For now, just log the accounts - full mapping would require
                    # more complex logic to match phone/email to accounts
                    for account in accounts:
                        logger.info(f"Account: {account[0]} - {account[1]}")

        except Exception as e:
            logger.error(f"Error adding account mapping: {e}")

    def get_migration_stats(self):
        """Get statistics about the migrated database"""
        if not os.path.exists(self.target_db_path):
            return None

        with sqlite3.connect(self.target_db_path) as conn:
            cursor = conn.cursor()

            stats = {}

            # Total messages
            cursor.execute("SELECT COUNT(*) FROM messages_with_contacts")
            stats["total_messages"] = cursor.fetchone()[0]

            # Messages by type
            cursor.execute(
                "SELECT is_from_me, COUNT(*) FROM messages_with_contacts GROUP BY is_from_me"
            )
            for row in cursor.fetchall():
                key = "sent_messages" if row[0] else "received_messages"
                stats[key] = row[1]

            # Unique contacts
            cursor.execute(
                "SELECT COUNT(DISTINCT phone_email) FROM messages_with_contacts WHERE phone_email IS NOT NULL"
            )
            stats["unique_contacts"] = cursor.fetchone()[0]

            # Service types
            cursor.execute(
                "SELECT service_type, COUNT(*) FROM messages_with_contacts GROUP BY service_type"
            )
            stats["services"] = dict(cursor.fetchall())

            return stats


def main():
    """CLI for running database migration"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate Messages database to joined format"
    )
    parser.add_argument(
        "--source", default="./data/chat_copy.db", help="Source Messages database"
    )
    parser.add_argument(
        "--target", default="./data/messages_joined.db", help="Target database path"
    )
    parser.add_argument(
        "--limit", type=int, help="Limit number of messages to migrate (for testing)"
    )
    parser.add_argument("--contacts", help="Path to contacts database")
    parser.add_argument(
        "--stats-only", action="store_true", help="Show stats only, don't migrate"
    )

    args = parser.parse_args()

    migrator = DatabaseMigrator(
        source_db_path=args.source,
        target_db_path=args.target,
        contacts_db_path=args.contacts,
    )

    if args.stats_only:
        stats = migrator.get_migration_stats()
        if stats:
            print("\n=== Migration Statistics ===")
            for key, value in stats.items():
                print(f"{key}: {value}")
        else:
            print("No migrated database found")
        return

    try:
        # Create schema
        migrator.create_target_schema()

        # Migrate data
        total = migrator.migrate_data(limit=args.limit)

        # Add account mapping
        migrator.add_account_mapping()

        # Show stats
        stats = migrator.get_migration_stats()
        print(f"\n=== Migration Complete ===")
        print(f"Total messages migrated: {total}")
        if stats:
            print(f"Sent messages: {stats.get('sent_messages', 0)}")
            print(f"Received messages: {stats.get('received_messages', 0)}")
            print(f"Unique contacts: {stats.get('unique_contacts', 0)}")
            print(f"Services: {stats.get('services', {})}")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    main()
