#!/usr/bin/env python3
"""
Populate handle_id for users in messages.db

This script processes handles from the Messages database and either:
1. Matches them to existing users in the messages.db users table
2. Creates new users for unmatched handles

Based on SERENE-47 requirements:
- Remove country code from handle.id and match against address book
- Create new users with empty names if no match found
- Test cases: +19495272398 -> Allison Shi (handle_id=3), wayne26110@gmail.com -> Wayne Ellerbe (handle_id=27)
"""

import sys
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add src to path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from src.database.manager import DatabaseManager
from src.database.messages_db import MessagesDatabase
from src.user.handle_matcher import HandleMatcher
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class HandleIdPopulator:
    """Populates handle_id values for users based on Messages database handles"""
    
    def __init__(
        self,
        chat_db_path: str = "./data/copy/chat_copy.db",
        messages_db_path: str = "./data/messages.db"
    ):
        """
        Initialize the populator
        
        Args:
            chat_db_path: Path to Messages database copy
            messages_db_path: Path to our messages database
        """
        self.chat_db_path = Path(chat_db_path)
        self.messages_db_path = Path(messages_db_path)
        self.messages_db = MessagesDatabase(str(messages_db_path))
        self.handle_matcher = HandleMatcher(str(messages_db_path))
        
    def extract_handles_from_messages_db(self) -> List[Tuple[int, str]]:
        """
        Extract all handles from the Messages database
        
        Returns:
            List of (handle_id, handle_id_value) tuples
        """
        if not self.chat_db_path.exists():
            logger.error(f"Messages database not found at {self.chat_db_path}")
            return []
        
        try:
            with sqlite3.connect(str(self.chat_db_path)) as conn:
                cursor = conn.cursor()
                
                # Get all handles with their ROWID and id
                cursor.execute("""
                    SELECT ROWID, id
                    FROM handle
                    ORDER BY ROWID
                """)
                
                handles = cursor.fetchall()
                logger.info(f"Extracted {len(handles)} handles from Messages database")
                return handles
                
        except sqlite3.Error as e:
            logger.error(f"Error extracting handles: {e}")
            return []
    
    def get_existing_users_with_handles(self) -> Dict[int, str]:
        """
        Get existing users that already have handle_id assigned
        
        Returns:
            Dictionary mapping handle_id to user_id
        """
        existing_users = self.messages_db.get_all_users()
        handle_to_user = {}
        
        for user in existing_users:
            if user.handle_id is not None:
                handle_to_user[user.handle_id] = user.user_id
        
        logger.info(f"Found {len(handle_to_user)} existing users with handle_id")
        return handle_to_user
    
    def process_handles(self) -> Dict[str, int]:
        """
        Process all handles and create/match users
        
        Returns:
            Dictionary with processing statistics
        """
        handles = self.extract_handles_from_messages_db()
        if not handles:
            logger.error("No handles found to process")
            return {'error': 'No handles found'}
        
        existing_handle_users = self.get_existing_users_with_handles()
        
        stats = {
            'total_handles': len(handles),
            'existing_users': len(existing_handle_users),
            'new_users_created': 0,
            'existing_users_matched': 0,
            'skipped_existing': 0,
            'errors': 0
        }
        
        for handle_id, handle_id_value in handles:
            try:
                # Skip if user already exists with this handle_id
                if handle_id in existing_handle_users:
                    logger.debug(f"Skipping handle_id {handle_id} - user already exists")
                    stats['skipped_existing'] += 1
                    continue
                
                # Try to match or create user
                user = self.handle_matcher.match_handle_to_user(handle_id, handle_id_value)
                
                if user:
                    if user.handle_id == handle_id:
                        stats['new_users_created'] += 1
                        logger.info(f"Created/matched user for handle_id {handle_id}: {user}")
                    else:
                        # Update existing user with handle_id
                        success = self.messages_db.update_user_handle_id(user.user_id, handle_id)
                        if success:
                            stats['existing_users_matched'] += 1
                            logger.info(f"Updated existing user {user.user_id} with handle_id {handle_id}")
                        else:
                            stats['errors'] += 1
                            logger.error(f"Failed to update user {user.user_id} with handle_id {handle_id}")
                else:
                    stats['errors'] += 1
                    logger.error(f"Failed to create/match user for handle_id {handle_id}")
                    
            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Error processing handle_id {handle_id} ({handle_id_value}): {e}")
        
        return stats
    
    def validate_test_cases(self) -> Dict[str, bool]:
        """
        Validate the specific test cases mentioned in the ticket
        
        Returns:
            Dictionary with validation results
        """
        validation_results = {}
        
        # Test case 1: +19495272398 -> Allison Shi (handle_id=3)
        user_handle_3 = self.messages_db.get_user_by_handle_id(3)
        if user_handle_3:
            is_allison = (
                "allison" in user_handle_3.first_name.lower() and
                "shi" in user_handle_3.last_name.lower()
            )
            validation_results['allison_shi_handle_3'] = is_allison
            logger.info(f"Handle 3 user: {user_handle_3} - Allison Shi match: {is_allison}")
        else:
            validation_results['allison_shi_handle_3'] = False
            logger.warning("No user found with handle_id=3")
        
        # Test case 2: wayne26110@gmail.com -> Wayne Ellerbe (handle_id=27)
        user_handle_27 = self.messages_db.get_user_by_handle_id(27)
        if user_handle_27:
            is_wayne = (
                "wayne" in user_handle_27.first_name.lower() and
                "ellerbe" in user_handle_27.last_name.lower()
            )
            validation_results['wayne_ellerbe_handle_27'] = is_wayne
            logger.info(f"Handle 27 user: {user_handle_27} - Wayne Ellerbe match: {is_wayne}")
        else:
            validation_results['wayne_ellerbe_handle_27'] = False
            logger.warning("No user found with handle_id=27")
        
        return validation_results
    
    def print_summary(self, stats: Dict[str, int], validation: Dict[str, bool]):
        """Print processing summary"""
        print("\n" + "="*60)
        print("HANDLE ID POPULATION SUMMARY")
        print("="*60)
        
        print("\nProcessing Statistics:")
        for key, value in stats.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
        
        print("\nTest Case Validation:")
        for test_case, passed in validation.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {test_case.replace('_', ' ').title()}: {status}")
        
        print("\nDatabase Information:")
        db_stats = self.messages_db.get_database_stats()
        print(f"  Total Users: {db_stats.get('total_users', 0)}")
        print(f"  Users with Phone: {db_stats.get('users_with_phone', 0)}")
        print(f"  Users with Email: {db_stats.get('users_with_email', 0)}")
        
        all_passed = all(validation.values())
        if all_passed:
            print("\n🎉 All test cases passed!")
        else:
            print("\n⚠️  Some test cases failed. Check the logs for details.")


def main():
    """Main execution function"""
    # Setup database copying first
    print("Setting up Messages database copy...")
    db_manager = DatabaseManager()
    
    if not db_manager.create_safe_copy():
        print("❌ Failed to create safe database copy")
        return 1
    
    print("✅ Database copy created successfully")
    
    # Initialize populator
    populator = HandleIdPopulator()
    
    # Ensure messages database exists
    if not populator.messages_db.database_exists():
        print("Creating messages database...")
        populator.messages_db.create_database()
    
    print("Starting handle ID population...")
    
    # Process handles
    stats = populator.process_handles()
    
    if 'error' in stats:
        print(f"❌ Error: {stats['error']}")
        return 1
    
    # Validate test cases
    validation = populator.validate_test_cases()
    
    # Print summary
    populator.print_summary(stats, validation)
    
    return 0 if all(validation.values()) else 1


if __name__ == "__main__":
    sys.exit(main())