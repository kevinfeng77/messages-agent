#!/usr/bin/env python3
"""
Validation script for the new messages table implementation.

This script validates:
1. Schema correctness and constraints
2. Data integrity and consistency 
3. Text decoding quality
4. Performance characteristics
5. Migration completeness

Usage:
    python scripts/validation/validate_messages_table.py
"""

import sys
import sqlite3
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from database.messages_db import MessagesDatabase
from messaging.decoder import extract_message_text
from utils.logger_config import get_logger

logger = get_logger(__name__)


class MessagesTableValidator:
    """Comprehensive validator for the messages table implementation"""

    def __init__(
        self,
        target_db_path: str = "./data/messages.db",
        source_db_path: str = "./data/chat_copy.db",
    ):
        self.target_db_path = Path(target_db_path)
        self.source_db_path = Path(source_db_path)
        self.messages_db = MessagesDatabase(str(self.target_db_path))
        self.validation_results = {
            "schema_validation": {},
            "data_integrity": {},
            "text_quality": {},
            "performance": {},
            "migration_completeness": {},
            "overall_status": "unknown",
            "validation_time": datetime.now().isoformat(),
        }

    def validate_schema(self) -> Dict[str, Any]:
        """
        Validate the messages table schema

        Returns:
            Dictionary with schema validation results
        """
        logger.info("Validating messages table schema...")
        results = {
            "table_exists": False,
            "correct_columns": False,
            "primary_key_correct": False,
            "indexes_present": False,
            "column_types_correct": False,
            "constraints_valid": False,
        }

        try:
            with sqlite3.connect(str(self.target_db_path)) as conn:
                cursor = conn.cursor()

                # Check if table exists
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
                )
                results["table_exists"] = cursor.fetchone() is not None

                if not results["table_exists"]:
                    logger.error("Messages table does not exist")
                    return results

                # Check column structure
                cursor.execute("PRAGMA table_info(messages)")
                columns = cursor.fetchall()
                
                expected_columns = {
                    "message_id": ("TEXT", 1, 1),  # (type, notnull, pk)
                    "user_id": ("TEXT", 1, 0),
                    "contents": ("TEXT", 1, 0),
                    "is_from_me": ("BOOLEAN", 0, 0),
                    "created_at": ("TEXT", 1, 0),
                }

                actual_columns = {}
                for column in columns:
                    cid, name, col_type, notnull, dflt_value, pk = column
                    actual_columns[name] = (col_type, notnull, pk)

                # Validate columns
                results["correct_columns"] = set(expected_columns.keys()) == set(actual_columns.keys())
                results["column_types_correct"] = all(
                    actual_columns.get(name) == expected
                    for name, expected in expected_columns.items()
                )

                # Check primary key
                primary_keys = [col[1] for col in columns if col[5] == 1]
                results["primary_key_correct"] = primary_keys == ["message_id"]

                # Check indexes
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='messages'"
                )
                indexes = {row[0] for row in cursor.fetchall()}
                
                expected_indexes = {
                    "idx_messages_message_id",
                    "idx_messages_user_id",
                    "idx_messages_created_at", 
                    "idx_messages_is_from_me"
                }
                
                results["indexes_present"] = expected_indexes.issubset(indexes)

                # Check constraints (basic validation)
                cursor.execute("SELECT COUNT(*) FROM messages WHERE message_id IS NULL")
                null_message_ids = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM messages WHERE user_id IS NULL")
                null_user_ids = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM messages WHERE contents IS NULL")
                null_contents = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM messages WHERE created_at IS NULL")
                null_created_at = cursor.fetchone()[0]

                results["constraints_valid"] = all([
                    null_message_ids == 0,
                    null_user_ids == 0,
                    null_contents == 0,
                    null_created_at == 0,
                ])

                logger.info(f"Schema validation results: {results}")
                return results

        except Exception as e:
            logger.error(f"Error during schema validation: {e}")
            results["error"] = str(e)
            return results

    def validate_data_integrity(self) -> Dict[str, Any]:
        """
        Validate data integrity in the messages table

        Returns:
            Dictionary with data integrity validation results
        """
        logger.info("Validating data integrity...")
        results = {
            "total_messages": 0,
            "unique_message_ids": True,
            "valid_timestamps": True,
            "valid_boolean_values": True,
            "non_empty_contents": True,
            "user_id_format_valid": True,
            "data_consistency": True,
        }

        try:
            # Get all messages
            all_messages = self.messages_db.get_all_messages()
            results["total_messages"] = len(all_messages)

            if results["total_messages"] == 0:
                logger.warning("No messages found in database")
                return results

            # Check unique message IDs
            message_ids = [msg["message_id"] for msg in all_messages]
            results["unique_message_ids"] = len(message_ids) == len(set(message_ids))

            # Validate timestamps
            invalid_timestamps = 0
            for msg in all_messages:
                try:
                    datetime.fromisoformat(msg["created_at"])
                except ValueError:
                    invalid_timestamps += 1
            
            results["valid_timestamps"] = invalid_timestamps == 0
            results["invalid_timestamp_count"] = invalid_timestamps

            # Validate boolean values
            invalid_booleans = 0
            for msg in all_messages:
                if not isinstance(msg["is_from_me"], bool):
                    invalid_booleans += 1
            
            results["valid_boolean_values"] = invalid_booleans == 0
            results["invalid_boolean_count"] = invalid_booleans

            # Check for empty contents
            empty_contents = sum(1 for msg in all_messages if not msg["contents"].strip())
            results["non_empty_contents"] = empty_contents == 0
            results["empty_contents_count"] = empty_contents

            # Validate user_id format (should not be empty)
            empty_user_ids = sum(1 for msg in all_messages if not msg["user_id"].strip())
            results["user_id_format_valid"] = empty_user_ids == 0
            results["empty_user_id_count"] = empty_user_ids

            # Check data consistency across operations
            sample_message = all_messages[0] if all_messages else None
            if sample_message:
                retrieved_message = self.messages_db.get_message_by_id(sample_message["message_id"])
                results["data_consistency"] = retrieved_message == sample_message

            logger.info(f"Data integrity validation results: {results}")
            return results

        except Exception as e:
            logger.error(f"Error during data integrity validation: {e}")
            results["error"] = str(e)
            return results

    def validate_text_quality(self) -> Dict[str, Any]:
        """
        Validate quality of decoded text content

        Returns:
            Dictionary with text quality validation results
        """
        logger.info("Validating text decoding quality...")
        results = {
            "total_messages_analyzed": 0,
            "messages_with_text": 0,
            "average_text_length": 0.0,
            "contains_emojis": False,
            "contains_special_chars": False,
            "text_encoding_valid": True,
            "suspicious_patterns": [],
        }

        try:
            all_messages = self.messages_db.get_all_messages()
            results["total_messages_analyzed"] = len(all_messages)

            if not all_messages:
                return results

            text_lengths = []
            encoding_errors = 0
            suspicious_patterns = []

            for msg in all_messages:
                content = msg["contents"]
                
                if content.strip():
                    results["messages_with_text"] += 1
                    text_lengths.append(len(content))

                    # Check for emojis (basic Unicode range check)
                    if any(ord(char) > 127 for char in content):
                        results["contains_emojis"] = True

                    # Check for special characters
                    special_chars = set("'\"&<>")
                    if any(char in content for char in special_chars):
                        results["contains_special_chars"] = True

                    # Check for encoding issues
                    try:
                        content.encode('utf-8').decode('utf-8')
                    except UnicodeError:
                        encoding_errors += 1

                    # Look for suspicious patterns that might indicate decoding issues
                    suspicious = [
                        "\\x" in content,  # Hex escape sequences
                        "\\u" in content,  # Unicode escape sequences
                        content.count("�") > 0,  # Replacement characters
                        len(content) > 0 and all(ord(c) < 32 for c in content[:10]),  # Control chars
                    ]
                    
                    if any(suspicious):
                        suspicious_patterns.append(msg["message_id"])

            if text_lengths:
                results["average_text_length"] = sum(text_lengths) / len(text_lengths)

            results["text_encoding_valid"] = encoding_errors == 0
            results["encoding_error_count"] = encoding_errors
            results["suspicious_patterns"] = suspicious_patterns[:10]  # Limit to first 10

            logger.info(f"Text quality validation results: {results}")
            return results

        except Exception as e:
            logger.error(f"Error during text quality validation: {e}")
            results["error"] = str(e)
            return results

    def validate_performance(self) -> Dict[str, Any]:
        """
        Validate performance characteristics of the messages table

        Returns:
            Dictionary with performance validation results
        """
        logger.info("Validating performance characteristics...")
        results = {
            "query_performance": {},
            "index_effectiveness": {},
            "database_size": 0,
        }

        try:
            # Check database file size
            if self.target_db_path.exists():
                results["database_size"] = self.target_db_path.stat().st_size

            # Test query performance
            performance_tests = [
                ("get_all_messages", lambda: self.messages_db.get_all_messages(limit=100)),
                ("get_message_by_id", lambda: self.messages_db.get_message_by_id("1")),
                ("get_messages_by_user", lambda: self.messages_db.get_messages_by_user("test_user", limit=50)),
            ]

            for test_name, test_func in performance_tests:
                start_time = time.time()
                try:
                    test_func()
                    end_time = time.time()
                    results["query_performance"][test_name] = {
                        "duration_ms": (end_time - start_time) * 1000,
                        "success": True,
                    }
                except Exception as e:
                    results["query_performance"][test_name] = {
                        "duration_ms": -1,
                        "success": False,
                        "error": str(e),
                    }

            # Test index effectiveness with EXPLAIN QUERY PLAN
            with sqlite3.connect(str(self.target_db_path)) as conn:
                cursor = conn.cursor()
                
                index_tests = [
                    ("message_id_lookup", "SELECT * FROM messages WHERE message_id = ?", ("test_id",)),
                    ("user_id_lookup", "SELECT * FROM messages WHERE user_id = ?", ("test_user",)),
                    ("timestamp_range", "SELECT * FROM messages WHERE created_at > ?", ("2023-01-01T00:00:00",)),
                ]

                for test_name, query, params in index_tests:
                    cursor.execute(f"EXPLAIN QUERY PLAN {query}", params)
                    plan = cursor.fetchall()
                    
                    # Check if index is being used (simplified check)
                    using_index = any("USING INDEX" in str(row) for row in plan)
                    results["index_effectiveness"][test_name] = {
                        "using_index": using_index,
                        "query_plan": str(plan),
                    }

            logger.info(f"Performance validation results: {results}")
            return results

        except Exception as e:
            logger.error(f"Error during performance validation: {e}")
            results["error"] = str(e)
            return results

    def validate_migration_completeness(self) -> Dict[str, Any]:
        """
        Validate completeness of migration from source database

        Returns:
            Dictionary with migration completeness validation results
        """
        logger.info("Validating migration completeness...")
        results = {
            "source_available": False,
            "target_message_count": 0,
            "source_message_count": 0,
            "migration_coverage": 0.0,
            "sample_messages_match": False,
        }

        try:
            # Check if source database exists
            results["source_available"] = self.source_db_path.exists()
            
            if not results["source_available"]:
                logger.warning("Source database not available for comparison")
                return results

            # Count messages in target
            target_messages = self.messages_db.get_all_messages()
            results["target_message_count"] = len(target_messages)

            # Count messages in source
            with sqlite3.connect(str(self.source_db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM message WHERE text IS NOT NULL OR attributedBody IS NOT NULL")
                results["source_message_count"] = cursor.fetchone()[0]

            # Calculate migration coverage
            if results["source_message_count"] > 0:
                results["migration_coverage"] = results["target_message_count"] / results["source_message_count"]

            # Sample validation: check if some messages from source appear in target
            if results["target_message_count"] > 0 and results["source_message_count"] > 0:
                with sqlite3.connect(str(self.source_db_path)) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT ROWID, text, attributedBody FROM message WHERE text IS NOT NULL LIMIT 5"
                    )
                    source_samples = cursor.fetchall()

                matches = 0
                for source_row in source_samples:
                    source_id, source_text, source_attributed = source_row
                    decoded_text = extract_message_text(source_text, source_attributed)
                    
                    # Look for this text in target messages
                    target_match = any(
                        msg["contents"] == decoded_text 
                        for msg in target_messages 
                        if decoded_text and decoded_text.strip()
                    )
                    
                    if target_match:
                        matches += 1

                results["sample_messages_match"] = matches > 0
                results["sample_match_count"] = matches
                results["sample_total"] = len(source_samples)

            logger.info(f"Migration completeness validation results: {results}")
            return results

        except Exception as e:
            logger.error(f"Error during migration completeness validation: {e}")
            results["error"] = str(e)
            return results

    def run_full_validation(self) -> Dict[str, Any]:
        """
        Run complete validation suite

        Returns:
            Dictionary with all validation results
        """
        logger.info("Starting full validation of messages table implementation...")

        # Run all validation checks
        self.validation_results["schema_validation"] = self.validate_schema()
        self.validation_results["data_integrity"] = self.validate_data_integrity()
        self.validation_results["text_quality"] = self.validate_text_quality()
        self.validation_results["performance"] = self.validate_performance()
        self.validation_results["migration_completeness"] = self.validate_migration_completeness()

        # Determine overall status
        critical_checks = [
            self.validation_results["schema_validation"].get("table_exists", False),
            self.validation_results["schema_validation"].get("correct_columns", False),
            self.validation_results["data_integrity"].get("unique_message_ids", False),
            self.validation_results["data_integrity"].get("valid_timestamps", False),
        ]

        warning_checks = [
            self.validation_results["text_quality"].get("text_encoding_valid", False),
            self.validation_results["migration_completeness"].get("migration_coverage", 0) > 0.8,
        ]

        if all(critical_checks):
            if all(warning_checks):
                self.validation_results["overall_status"] = "PASS"
            else:
                self.validation_results["overall_status"] = "PASS_WITH_WARNINGS"
        else:
            self.validation_results["overall_status"] = "FAIL"

        return self.validation_results

    def generate_validation_report(self) -> str:
        """
        Generate a human-readable validation report

        Returns:
            Formatted validation report string
        """
        if not self.validation_results or self.validation_results["overall_status"] == "unknown":
            return "Validation has not been run yet."

        report = []
        report.append("=" * 60)
        report.append("MESSAGES TABLE VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Validation Time: {self.validation_results['validation_time']}")
        report.append(f"Overall Status: {self.validation_results['overall_status']}")
        report.append("")

        # Schema Validation
        schema = self.validation_results["schema_validation"]
        report.append("SCHEMA VALIDATION:")
        report.append(f"  ✓ Table exists: {schema.get('table_exists', False)}")
        report.append(f"  ✓ Correct columns: {schema.get('correct_columns', False)}")
        report.append(f"  ✓ Primary key correct: {schema.get('primary_key_correct', False)}")
        report.append(f"  ✓ Indexes present: {schema.get('indexes_present', False)}")
        report.append(f"  ✓ Column types correct: {schema.get('column_types_correct', False)}")
        report.append(f"  ✓ Constraints valid: {schema.get('constraints_valid', False)}")
        report.append("")

        # Data Integrity
        integrity = self.validation_results["data_integrity"]
        report.append("DATA INTEGRITY:")
        report.append(f"  Total messages: {integrity.get('total_messages', 0)}")
        report.append(f"  ✓ Unique message IDs: {integrity.get('unique_message_ids', False)}")
        report.append(f"  ✓ Valid timestamps: {integrity.get('valid_timestamps', False)}")
        report.append(f"  ✓ Valid boolean values: {integrity.get('valid_boolean_values', False)}")
        report.append(f"  ✓ Non-empty contents: {integrity.get('non_empty_contents', False)}")
        report.append(f"  ✓ Valid user IDs: {integrity.get('user_id_format_valid', False)}")
        report.append("")

        # Text Quality
        text_quality = self.validation_results["text_quality"]
        report.append("TEXT QUALITY:")
        report.append(f"  Messages analyzed: {text_quality.get('total_messages_analyzed', 0)}")
        report.append(f"  Messages with text: {text_quality.get('messages_with_text', 0)}")
        report.append(f"  Average text length: {text_quality.get('average_text_length', 0):.1f}")
        report.append(f"  Contains emojis: {text_quality.get('contains_emojis', False)}")
        report.append(f"  ✓ Text encoding valid: {text_quality.get('text_encoding_valid', False)}")
        report.append("")

        # Performance
        performance = self.validation_results["performance"]
        report.append("PERFORMANCE:")
        report.append(f"  Database size: {performance.get('database_size', 0):,} bytes")
        
        query_perf = performance.get('query_performance', {})
        for test_name, results in query_perf.items():
            duration = results.get('duration_ms', -1)
            success = results.get('success', False)
            status = "✓" if success else "✗"
            report.append(f"  {status} {test_name}: {duration:.2f}ms")
        report.append("")

        # Migration Completeness
        migration = self.validation_results["migration_completeness"]
        report.append("MIGRATION COMPLETENESS:")
        report.append(f"  Source available: {migration.get('source_available', False)}")
        report.append(f"  Target messages: {migration.get('target_message_count', 0)}")
        report.append(f"  Source messages: {migration.get('source_message_count', 0)}")
        report.append(f"  Migration coverage: {migration.get('migration_coverage', 0):.1%}")
        report.append(f"  ✓ Sample messages match: {migration.get('sample_messages_match', False)}")
        report.append("")

        report.append("=" * 60)
        
        return "\n".join(report)


def main():
    """Main function to run messages table validation"""
    logger.info("Starting messages table validation...")

    # Initialize validator
    validator = MessagesTableValidator()

    # Run full validation
    results = validator.run_full_validation()

    # Generate and display report
    report = validator.generate_validation_report()
    print(report)

    # Log detailed results
    logger.info(f"Detailed validation results: {results}")

    # Return appropriate exit code
    status = results["overall_status"]
    if status == "PASS":
        logger.info("Messages table validation PASSED!")
        return 0
    elif status == "PASS_WITH_WARNINGS":
        logger.warning("Messages table validation PASSED with warnings")
        return 0
    else:
        logger.error("Messages table validation FAILED!")
        return 1


if __name__ == "__main__":
    exit(main())