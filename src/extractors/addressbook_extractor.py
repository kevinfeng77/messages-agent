"""AddressBook extractor for extracting user data from macOS address book databases"""

import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

from src.user.user import User
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class AddressBookExtractor:
    """Extracts user data from macOS address book databases"""

    def __init__(self):
        self.addressbook_root = Path.home() / "Library/Application Support/AddressBook"
        self.sources_dir = self.addressbook_root / "Sources"

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for consistency"""
        if not phone:
            return ""

        # Remove all non-digits
        normalized = "".join(filter(str.isdigit, phone))

        # If it starts with 1, remove it (US country code)
        if normalized.startswith("1") and len(normalized) == 11:
            normalized = normalized[1:]

        # Format as (XXX) XXX-XXXX if 10 digits
        if len(normalized) == 10:
            return f"({normalized[:3]}) {normalized[3:6]}-{normalized[6:]}"

        return phone  # Return original if can't normalize

    def _get_addressbook_databases(self) -> List[Path]:
        """Get all AddressBook database paths"""
        databases = []

        # Add main database if it exists
        main_db = self.addressbook_root / "AddressBook-v22.abcddb"
        if main_db.exists():
            databases.append(main_db)

        # Add all source databases
        if self.sources_dir.exists():
            for source_dir in self.sources_dir.iterdir():
                if source_dir.is_dir():
                    source_db = source_dir / "AddressBook-v22.abcddb"
                    if source_db.exists():
                        databases.append(source_db)

        return databases

    def extract_users(self) -> List[User]:
        """
        Extract users from all AddressBook databases

        Returns:
            List of User objects created from address book data
        """
        users = []
        databases = self._get_addressbook_databases()

        logger.info(f"Found {len(databases)} AddressBook databases to process")

        # Track users by phone/email to avoid duplicates
        seen_contacts = set()

        for db_path in databases:
            try:
                with sqlite3.connect(str(db_path)) as conn:
                    cursor = conn.cursor()

                    # Get all contacts with their phone numbers and emails
                    cursor.execute(
                        """
                        SELECT DISTINCT 
                            r.Z_PK,
                            r.ZFIRSTNAME,
                            r.ZLASTNAME,
                            p.ZFULLNUMBER,
                            e.ZADDRESS
                        FROM ZABCDRECORD r
                        LEFT JOIN ZABCDPHONENUMBER p ON r.Z_PK = p.ZOWNER
                        LEFT JOIN ZABCDEMAILADDRESS e ON r.Z_PK = e.ZOWNER
                        WHERE r.ZFIRSTNAME IS NOT NULL OR r.ZLASTNAME IS NOT NULL
                    """
                    )

                    records = cursor.fetchall()
                    logger.info(
                        f"Found {len(records)} contact records in {db_path.name}"
                    )

                    # Group records by person (Z_PK)
                    contacts_by_person = {}
                    for record in records:
                        z_pk, first_name, last_name, phone, email = record

                        if z_pk not in contacts_by_person:
                            contacts_by_person[z_pk] = {
                                "first_name": first_name or "",
                                "last_name": last_name or "",
                                "phones": set(),
                                "emails": set(),
                            }

                        if phone:
                            contacts_by_person[z_pk]["phones"].add(phone)
                        if email:
                            contacts_by_person[z_pk]["emails"].add(email.lower())

                    # Create User objects for each unique person
                    for z_pk, contact_data in contacts_by_person.items():
                        first_name = contact_data["first_name"]
                        last_name = contact_data["last_name"]

                        # Skip if no name
                        if not first_name and not last_name:
                            continue

                        # Get primary phone and email
                        primary_phone = ""
                        primary_email = ""

                        if contact_data["phones"]:
                            primary_phone = self._normalize_phone(
                                list(contact_data["phones"])[0]
                            )

                        if contact_data["emails"]:
                            primary_email = list(contact_data["emails"])[0]

                        # Skip if no contact methods
                        if not primary_phone and not primary_email:
                            continue

                        # Create unique identifier to avoid duplicates
                        contact_key = (
                            f"{first_name}:{last_name}:{primary_phone}:{primary_email}"
                        )
                        if contact_key in seen_contacts:
                            continue

                        seen_contacts.add(contact_key)

                        try:
                            user = User.from_address_book_record(
                                first_name=first_name,
                                last_name=last_name,
                                phone_number=primary_phone,
                                email=primary_email,
                            )
                            users.append(user)
                        except ValueError as e:
                            logger.warning(f"Skipping invalid user record: {e}")
                            continue

            except sqlite3.Error as e:
                logger.error(f"Error processing database {db_path}: {e}")
                continue

        logger.info(f"Extracted {len(users)} unique users from address book")
        return users

    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get statistics about address book extraction"""
        databases = self._get_addressbook_databases()

        stats = {
            "total_databases": len(databases),
            "database_paths": [str(db) for db in databases],
            "total_records": 0,
            "records_with_phone": 0,
            "records_with_email": 0,
            "unique_contacts": 0,
        }

        seen_contacts = set()

        for db_path in databases:
            try:
                with sqlite3.connect(str(db_path)) as conn:
                    cursor = conn.cursor()

                    # Count total records
                    cursor.execute(
                        "SELECT COUNT(*) FROM ZABCDRECORD WHERE ZFIRSTNAME IS NOT NULL OR ZLASTNAME IS NOT NULL"
                    )
                    db_records = cursor.fetchone()[0]
                    stats["total_records"] += db_records

                    # Count records with phone
                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT r.Z_PK) 
                        FROM ZABCDRECORD r 
                        JOIN ZABCDPHONENUMBER p ON r.Z_PK = p.ZOWNER
                        WHERE r.ZFIRSTNAME IS NOT NULL OR r.ZLASTNAME IS NOT NULL
                    """
                    )
                    phone_records = cursor.fetchone()[0]
                    stats["records_with_phone"] += phone_records

                    # Count records with email
                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT r.Z_PK) 
                        FROM ZABCDRECORD r 
                        JOIN ZABCDEMAILADDRESS e ON r.Z_PK = e.ZOWNER
                        WHERE r.ZFIRSTNAME IS NOT NULL OR r.ZLASTNAME IS NOT NULL
                    """
                    )
                    email_records = cursor.fetchone()[0]
                    stats["records_with_email"] += email_records

                    # Track unique contacts
                    cursor.execute(
                        """
                        SELECT r.ZFIRSTNAME, r.ZLASTNAME, p.ZFULLNUMBER, e.ZADDRESS
                        FROM ZABCDRECORD r
                        LEFT JOIN ZABCDPHONENUMBER p ON r.Z_PK = p.ZOWNER
                        LEFT JOIN ZABCDEMAILADDRESS e ON r.Z_PK = e.ZOWNER
                        WHERE r.ZFIRSTNAME IS NOT NULL OR r.ZLASTNAME IS NOT NULL
                    """
                    )

                    for record in cursor.fetchall():
                        first_name, last_name, phone, email = record
                        contact_key = f"{first_name}:{last_name}:{phone}:{email}"
                        seen_contacts.add(contact_key)

            except sqlite3.Error as e:
                logger.error(f"Error getting stats from {db_path}: {e}")

        stats["unique_contacts"] = len(seen_contacts)
        return stats
