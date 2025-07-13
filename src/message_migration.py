"""Message Migration - Update existing databases with decoded text"""

import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from .message_decoder import MessageDecoder, extract_message_text
except ImportError:
    from message_decoder import MessageDecoder, extract_message_text

logger = logging.getLogger(__name__)


class MessageMigration:
    """Handles migration of existing message databases to include decoded text"""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.backup_path = self.db_path.with_suffix(
            f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.decoder = MessageDecoder()

    def create_backup(self) -> bool:
        """Create a backup of the database before migration"""
        try:
            if not self.db_path.exists():
                logger.error(f"Database not found: {self.db_path}")
                return False

            shutil.copy2(self.db_path, self.backup_path)
            logger.info(f"Backup created: {self.backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

    def add_extracted_text_column(self) -> bool:
        """Add extracted_text column to the message table if it doesn't exist"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Check if column already exists
            cursor.execute("PRAGMA table_info(message)")
            columns = [row[1] for row in cursor.fetchall()]

            if "extracted_text" not in columns:
                # Add the new column
                cursor.execute("ALTER TABLE message ADD COLUMN extracted_text TEXT")
                logger.info("Added extracted_text column to message table")
            else:
                logger.info("extracted_text column already exists")

            conn.commit()
            conn.close()
            return True

        except sqlite3.Error as e:
            logger.error(f"Failed to add extracted_text column: {e}")
            return False

    def analyze_migration_scope(self) -> Dict[str, Any]:
        """Analyze how many messages need migration"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Get overall statistics
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN text IS NOT NULL AND text != '' THEN 1 END) as has_text,
                    COUNT(CASE WHEN (text IS NULL OR text = '') AND attributedBody IS NOT NULL THEN 1 END) as needs_migration,
                    COUNT(CASE WHEN attributedBody IS NULL THEN 1 END) as no_attributed_body
                FROM message
            """
            )

            total, has_text, needs_migration, no_attributed_body = cursor.fetchone()

            # Check if extracted_text column exists and has data
            cursor.execute("PRAGMA table_info(message)")
            columns = [row[1] for row in cursor.fetchall()]
            has_extracted_column = "extracted_text" in columns

            already_migrated = 0
            if has_extracted_column:
                cursor.execute(
                    """
                    SELECT COUNT(*) 
                    FROM message 
                    WHERE extracted_text IS NOT NULL AND extracted_text != ''
                """
                )
                already_migrated = cursor.fetchone()[0]

            conn.close()

            return {
                "total_messages": total,
                "has_text_column": has_text,
                "needs_migration": needs_migration,
                "no_attributed_body": no_attributed_body,
                "has_extracted_column": has_extracted_column,
                "already_migrated": already_migrated,
                "remaining_to_migrate": (
                    needs_migration - already_migrated
                    if has_extracted_column
                    else needs_migration
                ),
            }

        except sqlite3.Error as e:
            logger.error(f"Failed to analyze migration scope: {e}")
            return {}

    def migrate_messages(
        self, batch_size: int = 1000, max_batches: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Migrate messages by extracting text from attributedBody

        Args:
            batch_size: Number of messages to process per batch
            max_batches: Maximum number of batches to process (None for all)

        Returns:
            Migration statistics
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Get messages that need migration
            cursor.execute(
                """
                SELECT ROWID, text, attributedBody 
                FROM message 
                WHERE (text IS NULL OR text = '') 
                AND attributedBody IS NOT NULL
                AND (extracted_text IS NULL OR extracted_text = '')
                ORDER BY ROWID
            """
            )

            messages_to_migrate = cursor.fetchall()
            total_to_migrate = len(messages_to_migrate)

            if total_to_migrate == 0:
                logger.info("No messages need migration")
                conn.close()
                return {
                    "total_processed": 0,
                    "successful_extractions": 0,
                    "failed_extractions": 0,
                }

            logger.info(f"Found {total_to_migrate} messages to migrate")

            processed = 0
            successful_extractions = 0
            failed_extractions = 0
            batch_count = 0

            # Process in batches
            for i in range(0, total_to_migrate, batch_size):
                if max_batches and batch_count >= max_batches:
                    logger.info(f"Reached maximum batch limit: {max_batches}")
                    break

                batch = messages_to_migrate[i : i + batch_size]
                batch_count += 1

                logger.info(
                    f"Processing batch {batch_count}, messages {i+1}-{min(i+batch_size, total_to_migrate)}"
                )

                # Process each message in the batch
                updates = []
                for rowid, text, attributed_body in batch:
                    # Extract text
                    extracted_text = extract_message_text(text, attributed_body)

                    if extracted_text:
                        updates.append((extracted_text, rowid))
                        successful_extractions += 1
                    else:
                        failed_extractions += 1

                    processed += 1

                # Batch update extracted_text
                if updates:
                    cursor.executemany(
                        "UPDATE message SET extracted_text = ? WHERE ROWID = ?", updates
                    )
                    conn.commit()

                # Log progress
                if batch_count % 10 == 0:
                    success_rate = (successful_extractions / processed) * 100
                    logger.info(
                        f"Progress: {processed}/{total_to_migrate} ({success_rate:.1f}% success rate)"
                    )

            conn.close()

            # Log final statistics
            final_stats = {
                "total_processed": processed,
                "successful_extractions": successful_extractions,
                "failed_extractions": failed_extractions,
                "success_rate_percent": (
                    round((successful_extractions / processed) * 100, 2)
                    if processed > 0
                    else 0
                ),
                "decoder_stats": self.decoder.get_decode_stats(),
            }

            logger.info(f"Migration complete: {final_stats}")
            return final_stats

        except sqlite3.Error as e:
            logger.error(f"Migration failed: {e}")
            return {"error": str(e)}

    def validate_migration(self) -> Dict[str, Any]:
        """Validate the migration results"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Check migration results
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN text IS NOT NULL AND text != '' THEN 1 END) as has_text,
                    COUNT(CASE WHEN extracted_text IS NOT NULL AND extracted_text != '' THEN 1 END) as has_extracted_text,
                    COUNT(CASE WHEN 
                        (text IS NULL OR text = '') AND 
                        (extracted_text IS NOT NULL AND extracted_text != '') 
                    THEN 1 END) as recovered_from_attributed_body,
                    COUNT(CASE WHEN 
                        (text IS NULL OR text = '') AND 
                        (extracted_text IS NULL OR extracted_text = '') AND
                        attributedBody IS NOT NULL
                    THEN 1 END) as still_missing_text
                FROM message
            """
            )

            total, has_text, has_extracted, recovered, still_missing = cursor.fetchone()

            # Calculate coverage improvement
            original_coverage = (has_text / total) * 100 if total > 0 else 0
            new_coverage = ((has_text + recovered) / total) * 100 if total > 0 else 0
            improvement = new_coverage - original_coverage

            conn.close()

            validation_results = {
                "total_messages": total,
                "original_text_coverage_percent": round(original_coverage, 2),
                "new_text_coverage_percent": round(new_coverage, 2),
                "coverage_improvement_percent": round(improvement, 2),
                "messages_recovered": recovered,
                "still_missing_text": still_missing,
                "has_extracted_text_column": has_extracted,
            }

            logger.info(f"Migration validation: {validation_results}")
            return validation_results

        except sqlite3.Error as e:
            logger.error(f"Validation failed: {e}")
            return {"error": str(e)}

    def rollback_migration(self) -> bool:
        """Rollback migration by restoring from backup"""
        try:
            if not self.backup_path.exists():
                logger.error("No backup file found for rollback")
                return False

            shutil.copy2(self.backup_path, self.db_path)
            logger.info(f"Migration rolled back from backup: {self.backup_path}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False


def migrate_database(
    db_path: str,
    create_backup: bool = True,
    batch_size: int = 1000,
    max_batches: Optional[int] = None,
) -> bool:
    """
    Convenience function to perform complete database migration

    Args:
        db_path: Path to the database file
        create_backup: Whether to create a backup before migration
        batch_size: Number of messages to process per batch
        max_batches: Maximum number of batches (None for all)

    Returns:
        True if migration successful, False otherwise
    """
    migration = MessageMigration(Path(db_path))

    try:
        # Create backup if requested
        if create_backup:
            if not migration.create_backup():
                return False

        # Analyze scope
        scope = migration.analyze_migration_scope()
        logger.info(f"Migration scope: {scope}")

        if scope.get("remaining_to_migrate", 0) == 0:
            logger.info("No migration needed")
            return True

        # Add column if needed
        if not migration.add_extracted_text_column():
            return False

        # Perform migration
        results = migration.migrate_messages(
            batch_size=batch_size, max_batches=max_batches
        )

        if "error" in results:
            logger.error(f"Migration failed: {results['error']}")
            return False

        # Validate results
        validation = migration.validate_migration()

        if "error" in validation:
            logger.error(f"Validation failed: {validation['error']}")
            return False

        logger.info("Migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Migration process failed: {e}")
        return False