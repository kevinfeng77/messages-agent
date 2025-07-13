#!/usr/bin/env python3
"""
Validation script for SERENE-47: Create new users from handle

This script validates that the handle_id implementation works correctly
with the specific test cases mentioned in the ticket:
- +19495272398 should map to Allison Shi with handle_id = 3
- wayne26110@gmail.com should map to Wayne Ellerbe with handle_id = 27

It also provides comprehensive validation of the entire implementation.
"""

import sys
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Add src to path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from src.database.manager import DatabaseManager
from src.database.messages_db import MessagesDatabase
from src.user.handle_matcher import HandleMatcher
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class HandleIdValidator:
    """Validates the handle_id implementation and test cases"""
    
    def __init__(
        self,
        chat_db_path: str = "./data/copy/chat_copy.db",
        messages_db_path: str = "./data/messages.db"
    ):
        """
        Initialize the validator
        
        Args:
            chat_db_path: Path to Messages database copy
            messages_db_path: Path to our messages database
        """
        self.chat_db_path = Path(chat_db_path)
        self.messages_db_path = Path(messages_db_path)
        self.messages_db = MessagesDatabase(str(messages_db_path))
        self.handle_matcher = HandleMatcher(str(messages_db_path))
        
    def validate_database_schema(self) -> Dict[str, Any]:
        """
        Validate that the database schema is correct
        
        Returns:
            Dictionary with validation results
        """
        results = {}
        
        # Check database exists
        results['database_exists'] = self.messages_db.database_exists()
        
        # Check users table exists
        results['users_table_exists'] = self.messages_db.table_exists('users')
        
        # Check handle_id column exists
        schema = self.messages_db.get_table_schema('users')
        if schema:
            column_names = [col[1] for col in schema]
            results['handle_id_column_exists'] = 'handle_id' in column_names
            results['schema_columns'] = column_names
        else:
            results['handle_id_column_exists'] = False
            results['schema_columns'] = []
        
        return results
    
    def get_handle_info_from_messages_db(self, handle_id: int) -> Optional[Dict[str, Any]]:
        """
        Get handle information from the Messages database
        
        Args:
            handle_id: Handle ID to look up
            
        Returns:
            Dictionary with handle information or None
        """
        if not self.chat_db_path.exists():
            logger.error(f"Messages database not found at {self.chat_db_path}")
            return None
        
        try:
            with sqlite3.connect(str(self.chat_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT ROWID, id, country, service
                    FROM handle
                    WHERE ROWID = ?
                """, (handle_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'handle_id': row[0],
                        'id': row[1],
                        'country': row[2],
                        'service': row[3]
                    }
                
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Error getting handle info: {e}")
            return None
    
    def validate_test_case_allison_shi(self) -> Dict[str, Any]:
        """
        Validate the Allison Shi test case
        +19495272398 should map to user with name Allison Shi and handle_id = 3
        
        Returns:
            Dictionary with validation results
        """
        results = {}
        
        # Get handle information from Messages database
        handle_info = self.get_handle_info_from_messages_db(3)
        results['handle_3_info'] = handle_info
        
        if handle_info:
            results['handle_3_id_value'] = handle_info['id']
            results['handle_3_is_target_phone'] = handle_info['id'] == '+19495272398'
        else:
            results['handle_3_id_value'] = None
            results['handle_3_is_target_phone'] = False
        
        # Get user from our database
        user = self.messages_db.get_user_by_handle_id(3)
        results['user_exists'] = user is not None
        
        if user:
            results['user_info'] = {
                'user_id': user.user_id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone_number': user.phone_number,
                'email': user.email,
                'handle_id': user.handle_id
            }
            
            # Check if name matches Allison Shi
            first_match = 'allison' in user.first_name.lower()
            last_match = 'shi' in user.last_name.lower()
            results['name_matches_allison_shi'] = first_match and last_match
            results['first_name_match'] = first_match
            results['last_name_match'] = last_match
            
            # Check handle_id is correct
            results['handle_id_correct'] = user.handle_id == 3
            
            # Overall test result
            results['test_case_passes'] = (
                results['handle_3_is_target_phone'] and
                results['name_matches_allison_shi'] and
                results['handle_id_correct']
            )
        else:
            results['user_info'] = None
            results['name_matches_allison_shi'] = False
            results['handle_id_correct'] = False
            results['test_case_passes'] = False
        
        return results
    
    def validate_test_case_wayne_ellerbe(self) -> Dict[str, Any]:
        """
        Validate the Wayne Ellerbe test case
        wayne26110@gmail.com should map to Wayne Ellerbe with handle_id = 27
        
        Returns:
            Dictionary with validation results
        """
        results = {}
        
        # Get handle information from Messages database
        handle_info = self.get_handle_info_from_messages_db(27)
        results['handle_27_info'] = handle_info
        
        if handle_info:
            results['handle_27_id_value'] = handle_info['id']
            results['handle_27_is_target_email'] = handle_info['id'] == 'wayne26110@gmail.com'
        else:
            results['handle_27_id_value'] = None
            results['handle_27_is_target_email'] = False
        
        # Get user from our database
        user = self.messages_db.get_user_by_handle_id(27)
        results['user_exists'] = user is not None
        
        if user:
            results['user_info'] = {
                'user_id': user.user_id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone_number': user.phone_number,
                'email': user.email,
                'handle_id': user.handle_id
            }
            
            # Check if name matches Wayne Ellerbe
            first_match = 'wayne' in user.first_name.lower()
            last_match = 'ellerbe' in user.last_name.lower()
            results['name_matches_wayne_ellerbe'] = first_match and last_match
            results['first_name_match'] = first_match
            results['last_name_match'] = last_match
            
            # Check handle_id is correct
            results['handle_id_correct'] = user.handle_id == 27
            
            # Overall test result
            results['test_case_passes'] = (
                results['handle_27_is_target_email'] and
                results['name_matches_wayne_ellerbe'] and
                results['handle_id_correct']
            )
        else:
            results['user_info'] = None
            results['name_matches_wayne_ellerbe'] = False
            results['handle_id_correct'] = False
            results['test_case_passes'] = False
        
        return results
    
    def validate_phone_normalization(self) -> Dict[str, Any]:
        """
        Validate phone number normalization functionality
        
        Returns:
            Dictionary with validation results
        """
        results = {}
        
        test_cases = [
            ("+19495272398", "9495272398"),  # Remove country code
            ("+15551234567", "5551234567"),
            ("19495272398", "9495272398"),   # No + prefix
            ("5551234567", "5551234567"),    # Already 10 digits
        ]
        
        for input_phone, expected in test_cases:
            extracted = self.handle_matcher.extract_phone_from_handle_id(input_phone)
            results[f'extract_{input_phone}'] = {
                'input': input_phone,
                'extracted': extracted,
                'expected': expected,
                'correct': extracted == expected
            }
        
        return results
    
    def validate_fallback_user_creation(self) -> Dict[str, Any]:
        """
        Validate that fallback users are created correctly for unmatched handles
        
        Returns:
            Dictionary with validation results
        """
        results = {}
        
        # Test with a phone number that shouldn't match any contacts
        test_phone = "+15559999999"
        test_handle_id = 9999
        
        # First check if this handle_id already exists
        existing_user = self.messages_db.get_user_by_handle_id(test_handle_id)
        if existing_user:
            # Clean up for test
            # Note: In a real scenario, we'd use a test database
            results['cleanup_needed'] = True
        else:
            results['cleanup_needed'] = False
        
        # Mock the matching process by calling directly with non-matching data
        try:
            # This should create a fallback user
            user = self.handle_matcher._create_fallback_user(test_phone, test_handle_id)
            
            results['fallback_user_created'] = user is not None
            if user:
                results['fallback_user_info'] = {
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone_number': user.phone_number,
                    'email': user.email,
                    'handle_id': user.handle_id
                }
                
                # Check that names are empty as specified
                results['first_name_empty'] = user.first_name == ""
                results['last_name_empty'] = user.last_name == ""
                results['handle_id_correct'] = user.handle_id == test_handle_id
                results['phone_extracted_correctly'] = user.phone_number == "5559999999"
                
                results['fallback_validation_passes'] = (
                    results['first_name_empty'] and
                    results['last_name_empty'] and
                    results['handle_id_correct'] and
                    results['phone_extracted_correctly']
                )
            else:
                results['fallback_validation_passes'] = False
        
        except Exception as e:
            results['fallback_user_created'] = False
            results['error'] = str(e)
            results['fallback_validation_passes'] = False
        
        return results
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive database statistics
        
        Returns:
            Dictionary with database statistics
        """
        stats = self.messages_db.get_database_stats()
        
        # Add handle_id specific statistics
        try:
            all_users = self.messages_db.get_all_users()
            users_with_handle_id = [u for u in all_users if u.handle_id is not None]
            users_without_handle_id = [u for u in all_users if u.handle_id is None]
            
            stats['users_with_handle_id'] = len(users_with_handle_id)
            stats['users_without_handle_id'] = len(users_without_handle_id)
            
            if users_with_handle_id:
                handle_ids = [u.handle_id for u in users_with_handle_id]
                stats['min_handle_id'] = min(handle_ids)
                stats['max_handle_id'] = max(handle_ids)
                stats['unique_handle_ids'] = len(set(handle_ids))
            else:
                stats['min_handle_id'] = None
                stats['max_handle_id'] = None
                stats['unique_handle_ids'] = 0
                
        except Exception as e:
            stats['handle_id_stats_error'] = str(e)
        
        return stats
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """
        Run all validation tests
        
        Returns:
            Dictionary with all validation results
        """
        results = {}
        
        print("Running comprehensive validation...")
        
        # Schema validation
        print("  Validating database schema...")
        results['schema'] = self.validate_database_schema()
        
        # Test case validations
        print("  Validating Allison Shi test case...")
        results['allison_shi'] = self.validate_test_case_allison_shi()
        
        print("  Validating Wayne Ellerbe test case...")
        results['wayne_ellerbe'] = self.validate_test_case_wayne_ellerbe()
        
        # Phone normalization validation
        print("  Validating phone normalization...")
        results['phone_normalization'] = self.validate_phone_normalization()
        
        # Fallback user creation validation
        print("  Validating fallback user creation...")
        results['fallback_users'] = self.validate_fallback_user_creation()
        
        # Database statistics
        print("  Gathering database statistics...")
        results['database_stats'] = self.get_database_statistics()
        
        return results
    
    def print_validation_summary(self, results: Dict[str, Any]):
        """Print a comprehensive validation summary"""
        print("\n" + "="*80)
        print("HANDLE ID IMPLEMENTATION VALIDATION SUMMARY")
        print("="*80)
        
        # Schema validation
        schema = results.get('schema', {})
        print(f"\n📋 Database Schema:")
        print(f"  Database exists: {'✅' if schema.get('database_exists') else '❌'}")
        print(f"  Users table exists: {'✅' if schema.get('users_table_exists') else '❌'}")
        print(f"  Handle_id column exists: {'✅' if schema.get('handle_id_column_exists') else '❌'}")
        
        # Test cases
        print(f"\n🧪 Test Cases:")
        
        # Allison Shi test case
        allison = results.get('allison_shi', {})
        allison_pass = allison.get('test_case_passes', False)
        print(f"  Allison Shi (+19495272398 → handle_id=3): {'✅ PASS' if allison_pass else '❌ FAIL'}")
        if not allison_pass:
            print(f"    Handle 3 has correct phone: {'✅' if allison.get('handle_3_is_target_phone') else '❌'}")
            print(f"    User exists: {'✅' if allison.get('user_exists') else '❌'}")
            print(f"    Name matches: {'✅' if allison.get('name_matches_allison_shi') else '❌'}")
            print(f"    Handle ID correct: {'✅' if allison.get('handle_id_correct') else '❌'}")
        
        # Wayne Ellerbe test case
        wayne = results.get('wayne_ellerbe', {})
        wayne_pass = wayne.get('test_case_passes', False)
        print(f"  Wayne Ellerbe (wayne26110@gmail.com → handle_id=27): {'✅ PASS' if wayne_pass else '❌ FAIL'}")
        if not wayne_pass:
            print(f"    Handle 27 has correct email: {'✅' if wayne.get('handle_27_is_target_email') else '❌'}")
            print(f"    User exists: {'✅' if wayne.get('user_exists') else '❌'}")
            print(f"    Name matches: {'✅' if wayne.get('name_matches_wayne_ellerbe') else '❌'}")
            print(f"    Handle ID correct: {'✅' if wayne.get('handle_id_correct') else '❌'}")
        
        # Phone normalization
        phone_norm = results.get('phone_normalization', {})
        phone_tests_passed = all(test.get('correct', False) for test in phone_norm.values())
        print(f"  Phone normalization: {'✅ PASS' if phone_tests_passed else '❌ FAIL'}")
        
        # Fallback users
        fallback = results.get('fallback_users', {})
        fallback_pass = fallback.get('fallback_validation_passes', False)
        print(f"  Fallback user creation: {'✅ PASS' if fallback_pass else '❌ FAIL'}")
        
        # Database statistics
        stats = results.get('database_stats', {})
        print(f"\n📊 Database Statistics:")
        print(f"  Total users: {stats.get('total_users', 0)}")
        print(f"  Users with handle_id: {stats.get('users_with_handle_id', 0)}")
        print(f"  Users without handle_id: {stats.get('users_without_handle_id', 0)}")
        print(f"  Unique handle_ids: {stats.get('unique_handle_ids', 0)}")
        if stats.get('min_handle_id') is not None:
            print(f"  Handle ID range: {stats.get('min_handle_id')} - {stats.get('max_handle_id')}")
        
        # Overall result
        critical_tests = [allison_pass, wayne_pass, phone_tests_passed]
        all_critical_passed = all(critical_tests)
        
        print(f"\n🎯 Overall Result:")
        if all_critical_passed:
            print("  🎉 ALL CRITICAL TESTS PASSED! Implementation is working correctly.")
        else:
            print("  ⚠️  Some critical tests failed. Review the details above.")
        
        return all_critical_passed


def main():
    """Main execution function"""
    # Setup database copying first
    print("Setting up Messages database copy...")
    db_manager = DatabaseManager()
    
    if not db_manager.create_safe_copy():
        print("❌ Failed to create safe database copy")
        return 1
    
    print("✅ Database copy created successfully")
    
    # Initialize validator
    validator = HandleIdValidator()
    
    # Check if messages database exists
    if not validator.messages_db.database_exists():
        print("❌ Messages database not found. Please run populate_handle_ids.py first.")
        return 1
    
    # Run validation
    results = validator.run_comprehensive_validation()
    
    # Print summary
    all_passed = validator.print_validation_summary(results)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())