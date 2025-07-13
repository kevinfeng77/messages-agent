#!/usr/bin/env python3
"""Chat Migration Validation Script - Verify specific chat requirements"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add the src directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database.messages_db import MessagesDatabase
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class ChatMigrationValidator:
    """Validates chat migration results and specific requirements"""

    def __init__(
        self,
        source_db_path: str = "./data/chat_copy.db",
        target_db_path: str = "./data/messages.db",
    ):
        self.source_db_path = Path(source_db_path)
        self.target_db_path = Path(target_db_path)
        self.messages_db = MessagesDatabase(str(target_db_path))

    def validate_quantabes_chat(self) -> bool:
        """
        Validate that Quantabes chat contains John Wang and Eric Mueller

        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating Quantabes chat...")

        # Step 1: Find Quantabes chat
        quantabes_chats = self.messages_db.get_chats_by_display_name("Quantabes")

        if not quantabes_chats:
            logger.error("Quantabes chat not found in migrated chats")
            return False

        if len(quantabes_chats) > 1:
            logger.warning(f"Multiple Quantabes chats found: {len(quantabes_chats)}")

        quantabes_chat = quantabes_chats[0]
        logger.info(f"Found Quantabes chat: {quantabes_chat}")

        # Step 2: Get user IDs in the chat
        user_ids = quantabes_chat.get("user_ids", [])

        if not user_ids:
            logger.error("Quantabes chat has no users")
            return False

        logger.info(f"Quantabes chat has {len(user_ids)} users: {user_ids}")

        # Step 3: Get user details for each user_id
        users_in_chat = []
        for user_id in user_ids:
            user = self.messages_db.get_user_by_id(user_id)
            if user:
                users_in_chat.append(user)
                logger.info(
                    f"User in chat: {user.first_name} {user.last_name} ({user.user_id})"
                )
            else:
                logger.warning(f"User with ID {user_id} not found in users table")

        # Step 4: Check for John Wang and Eric Mueller
        found_john = False
        found_eric = False

        for user in users_in_chat:
            full_name = f"{user.first_name} {user.last_name}"
            if full_name == "John Wang":
                found_john = True
                logger.info(f"✓ Found John Wang: {user.user_id}")
            elif full_name == "Eric Mueller":
                found_eric = True
                logger.info(f"✓ Found Eric Mueller: {user.user_id}")

        # Step 5: Validation result
        if found_john and found_eric:
            logger.info(
                "✅ Quantabes chat validation PASSED - Contains both John Wang and Eric Mueller"
            )
            return True
        else:
            missing = []
            if not found_john:
                missing.append("John Wang")
            if not found_eric:
                missing.append("Eric Mueller")

            logger.error(
                f"❌ Quantabes chat validation FAILED - Missing: {', '.join(missing)}"
            )
            return False

    def validate_migration_completeness(self) -> Dict:
        """
        Validate overall migration completeness

        Returns:
            Dictionary with validation results
        """
        logger.info("Validating migration completeness...")

        results = {"validation_passed": True, "errors": [], "warnings": [], "stats": {}}

        try:
            # Check if source database exists
            if not self.source_db_path.exists():
                results["errors"].append(
                    f"Source database not found: {self.source_db_path}"
                )
                results["validation_passed"] = False
                return results

            # Check if target database exists
            if not self.target_db_path.exists():
                results["errors"].append(
                    f"Target database not found: {self.target_db_path}"
                )
                results["validation_passed"] = False
                return results

            # Get source chat count
            with sqlite3.connect(str(self.source_db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM chat")
                source_chat_count = cursor.fetchone()[0]

            # Get target chat count
            target_chats = self.messages_db.get_all_chats()
            target_chat_count = len(target_chats)

            results["stats"]["source_chats"] = source_chat_count
            results["stats"]["target_chats"] = target_chat_count
            results["stats"]["migration_rate"] = (
                round((target_chat_count / source_chat_count) * 100, 2)
                if source_chat_count > 0
                else 0
            )

            # Check migration completeness
            if target_chat_count == 0:
                results["errors"].append("No chats found in target database")
                results["validation_passed"] = False
            elif target_chat_count < source_chat_count:
                results["warnings"].append(
                    f"Not all chats migrated: {target_chat_count}/{source_chat_count}"
                )

            # Check for chats with users
            chats_with_users = len([c for c in target_chats if c["user_ids"]])
            chats_without_users = target_chat_count - chats_with_users

            results["stats"]["chats_with_users"] = chats_with_users
            results["stats"]["chats_without_users"] = chats_without_users

            if chats_without_users > 0:
                results["warnings"].append(
                    f"{chats_without_users} chats have no associated users"
                )

            # Check table structure (normalized design)
            chats_schema = self.messages_db.get_table_schema("chats")
            if not chats_schema:
                results["errors"].append("Chats table schema could not be retrieved")
                results["validation_passed"] = False
            else:
                expected_columns = [
                    "chat_id",
                    "display_name",
                ]  # users field removed in normalized design
                actual_columns = [col[1] for col in chats_schema]
                missing_columns = [
                    col for col in expected_columns if col not in actual_columns
                ]

                if missing_columns:
                    results["errors"].append(
                        f"Missing columns in chats table: {missing_columns}"
                    )
                    results["validation_passed"] = False

                results["stats"]["chats_table_columns"] = actual_columns

            # Check chat_users table structure
            chat_users_schema = self.messages_db.get_table_schema("chat_users")
            if not chat_users_schema:
                results["errors"].append(
                    "Chat_users table schema could not be retrieved"
                )
                results["validation_passed"] = False
            else:
                expected_chat_users_columns = ["chat_id", "user_id"]
                actual_chat_users_columns = [col[1] for col in chat_users_schema]
                missing_chat_users_columns = [
                    col
                    for col in expected_chat_users_columns
                    if col not in actual_chat_users_columns
                ]

                if missing_chat_users_columns:
                    results["errors"].append(
                        f"Missing columns in chat_users table: {missing_chat_users_columns}"
                    )
                    results["validation_passed"] = False

                results["stats"]["chat_users_table_columns"] = actual_chat_users_columns

        except Exception as e:
            results["errors"].append(f"Validation error: {str(e)}")
            results["validation_passed"] = False

        return results

    def get_chat_samples(self, limit: int = 5) -> List[Dict]:
        """
        Get sample chats for manual inspection

        Args:
            limit: Number of sample chats to return

        Returns:
            List of chat dictionaries with user details
        """
        try:
            chats = self.messages_db.get_all_chats(limit=limit)
            detailed_chats = []

            for chat in chats:
                detailed_chat = chat.copy()
                user_details = []

                for user_id in chat.get("user_ids", []):
                    user = self.messages_db.get_user_by_id(user_id)
                    if user:
                        user_details.append(
                            {
                                "user_id": user.user_id,
                                "name": f"{user.first_name} {user.last_name}",
                                "phone": user.phone_number,
                                "email": user.email,
                            }
                        )

                detailed_chat["user_details"] = user_details
                detailed_chats.append(detailed_chat)

            return detailed_chats

        except Exception as e:
            logger.error(f"Error getting chat samples: {e}")
            return []

    def run_full_validation(self) -> bool:
        """
        Run complete validation suite

        Returns:
            True if all validations pass, False otherwise
        """
        logger.info("=== Running Full Chat Migration Validation ===")

        # Validation 1: Migration completeness
        logger.info("\n1. Validating migration completeness...")
        completeness_results = self.validate_migration_completeness()

        for error in completeness_results["errors"]:
            logger.error(f"❌ {error}")

        for warning in completeness_results["warnings"]:
            logger.warning(f"⚠️  {warning}")

        logger.info(f"Migration stats: {completeness_results['stats']}")

        # Validation 2: Quantabes chat requirement
        logger.info("\n2. Validating Quantabes chat requirement...")
        quantabes_valid = self.validate_quantabes_chat()

        # Validation 3: Sample inspection
        logger.info("\n3. Sample chat inspection...")
        samples = self.get_chat_samples(5)
        for i, chat in enumerate(samples, 1):
            logger.info(
                f"Sample {i}: {chat['display_name']} (ID: {chat['chat_id']}) - {len(chat['user_details'])} users"
            )
            for user in chat["user_details"]:
                logger.info(f"  - {user['name']} ({user['user_id']})")

        # Overall result
        overall_success = completeness_results["validation_passed"] and quantabes_valid

        if overall_success:
            logger.info("\n✅ ALL VALIDATIONS PASSED")
        else:
            logger.error("\n❌ VALIDATION FAILED")

        return overall_success


def main():
    """Main function to run validation"""
    logger.info("=== Chat Migration Validation Script ===")

    # Initialize validator
    validator = ChatMigrationValidator()

    # Run full validation
    success = validator.run_full_validation()

    if success:
        logger.info("Chat migration validation completed successfully!")
        sys.exit(0)
    else:
        logger.error("Chat migration validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
