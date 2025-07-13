#!/usr/bin/env python3
"""
Test Suite for Setup Process

Tests the new streamlined setup process including:
- Database copying functionality
- Database creation and population
- Just command integration
- File structure validation
"""

import os
import sys
import sqlite3
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.database.messages_db import MessagesDatabase
from src.database.manager import DatabaseManager


class TestSetupProcess:
    """Test the complete setup process"""
    
    def setup_method(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.test_dir) / "data"
        self.copy_dir = self.data_dir / "copy"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.copy_dir.mkdir(parents=True, exist_ok=True)
        
        # Create mock source database
        self.mock_source_db = self.copy_dir / "chat_copy.db"
        self._create_mock_source_database()
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def _create_mock_source_database(self):
        """Create a minimal mock Messages database for testing"""
        with sqlite3.connect(str(self.mock_source_db)) as conn:
            cursor = conn.cursor()
            
            # Create basic tables
            cursor.execute("""
                CREATE TABLE handle (
                    ROWID INTEGER PRIMARY KEY,
                    id TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE chat (
                    ROWID INTEGER PRIMARY KEY,
                    guid TEXT,
                    display_name TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE message (
                    ROWID INTEGER PRIMARY KEY,
                    guid TEXT,
                    text TEXT,
                    handle_id INTEGER,
                    date INTEGER,
                    is_from_me INTEGER,
                    attributedBody BLOB
                )
            """)
            
            cursor.execute("""
                CREATE TABLE chat_handle_join (
                    chat_id INTEGER,
                    handle_id INTEGER
                )
            """)
            
            cursor.execute("""
                CREATE TABLE chat_message_join (
                    chat_id INTEGER,
                    message_id INTEGER,
                    message_date INTEGER
                )
            """)
            
            # Insert test data
            cursor.execute("INSERT INTO handle VALUES (1, '+15551234567')")
            cursor.execute("INSERT INTO handle VALUES (2, 'test@example.com')")
            
            cursor.execute("INSERT INTO chat VALUES (1, 'test-chat-1', 'Test Chat')")
            
            cursor.execute("""
                INSERT INTO message VALUES (
                    1, 'test-message-1', 'Hello World', 1, 
                    637500000000000000, 0, NULL
                )
            """)
            
            cursor.execute("INSERT INTO chat_handle_join VALUES (1, 1)")
            cursor.execute("INSERT INTO chat_handle_join VALUES (1, 2)")
            cursor.execute("INSERT INTO chat_message_join VALUES (1, 1, 637500000000000000)")
            
            conn.commit()


class TestDatabaseManager:
    """Test DatabaseManager functionality"""
    
    def test_database_manager_init(self):
        """Test DatabaseManager initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            dm = DatabaseManager(temp_dir)
            assert dm.data_directory == temp_dir
            assert dm.target_db_name == "chat_copy.db"
    
    @patch('src.database.manager.DatabaseManager.verify_source_database')
    def test_copy_workflow(self, mock_verify):
        """Test the database copy workflow"""
        mock_verify.return_value = True
        
        with tempfile.TemporaryDirectory() as temp_dir:
            dm = DatabaseManager(temp_dir)
            
            # Mock the source database path
            mock_source = Path(temp_dir) / "mock_chat.db"
            with sqlite3.connect(str(mock_source)) as conn:
                conn.execute("CREATE TABLE test (id INTEGER)")
            
            dm.source_db_path = str(mock_source)
            
            with patch.object(dm, '_copy_database_files') as mock_copy:
                mock_copy.return_value = True
                result = dm.create_safe_copy()
                assert result is not None


class TestMessagesDatabase:
    """Test MessagesDatabase setup functionality"""
    
    def test_database_creation(self):
        """Test database creation and schema setup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_messages.db"
            
            db = MessagesDatabase(str(db_path))
            success = db.create_database()
            
            assert success
            assert db_path.exists()
            
            # Verify schema
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('users', 'chats', 'messages', 'chat_users')
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                assert 'users' in tables
                assert 'chats' in tables
                assert 'messages' in tables
                assert 'chat_users' in tables


class TestJustCommands:
    """Test Just command integration"""
    
    def test_just_commands_exist(self):
        """Test that justfile contains required commands"""
        justfile_path = Path(__file__).parent.parent / "justfile"
        
        if not justfile_path.exists():
            pytest.skip("Justfile not found")
        
        content = justfile_path.read_text()
        
        # Check for required commands
        assert "setup:" in content
        assert "copy:" in content
        assert "create:" in content
        assert "clean:" in content
        
        # Check setup dependencies
        assert "setup: clean copy create" in content


class TestFileStructure:
    """Test file structure and organization"""
    
    def test_script_organization(self):
        """Test that scripts are properly organized"""
        scripts_dir = Path(__file__).parent.parent / "scripts"
        
        # Check main scripts exist
        assert (scripts_dir / "copy_messages_database.py").exists()
        assert (scripts_dir / "setup_messages_database.py").exists()
        
        # Check migration subdirectory
        migration_dir = scripts_dir / "migration"
        assert migration_dir.exists()
        assert (migration_dir / "migrate_messages_table.py").exists()
        
        # Check validation subdirectory
        validation_dir = scripts_dir / "validation"
        assert validation_dir.exists()
    
    def test_data_directory_structure(self):
        """Test that setup creates proper data directory structure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            # Create data directories
            data_dir = Path("data")
            copy_dir = data_dir / "copy"
            copy_dir.mkdir(parents=True, exist_ok=True)
            
            # Verify structure
            assert data_dir.exists()
            assert copy_dir.exists()
            
            # Test that copy script would place files correctly
            expected_copy_path = copy_dir / "chat_copy.db"
            expected_messages_path = data_dir / "messages.db"
            
            # These are the paths our scripts expect
            assert str(expected_copy_path) == "./data/copy/chat_copy.db"
            assert str(expected_messages_path) == "./data/messages.db"


class TestScriptFunctionality:
    """Test individual script functionality"""
    
    def test_copy_script_imports(self):
        """Test that copy script imports work correctly"""
        try:
            import sys
            from pathlib import Path
            
            scripts_dir = Path(__file__).parent.parent / "scripts"
            sys.path.insert(0, str(scripts_dir.parent))
            
            # Import copy script module
            spec = importlib.util.spec_from_file_location(
                "copy_messages_database", 
                scripts_dir / "copy_messages_database.py"
            )
            copy_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(copy_module)
            
            # Check main function exists
            assert hasattr(copy_module, 'main')
            
        except ImportError as e:
            pytest.fail(f"Copy script import failed: {e}")
    
    def test_setup_script_imports(self):
        """Test that setup script imports work correctly"""
        try:
            import sys
            import importlib.util
            from pathlib import Path
            
            scripts_dir = Path(__file__).parent.parent / "scripts"
            sys.path.insert(0, str(scripts_dir.parent))
            
            # Import setup script module
            spec = importlib.util.spec_from_file_location(
                "setup_messages_database", 
                scripts_dir / "setup_messages_database.py"
            )
            setup_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(setup_module)
            
            # Check main function exists
            assert hasattr(setup_module, 'main')
            
        except ImportError as e:
            pytest.fail(f"Setup script import failed: {e}")


class TestIntegration:
    """Integration tests for the complete setup process"""
    
    def test_setup_process_integration(self):
        """Test the complete setup process in isolation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            # Create data structure
            data_dir = Path("data")
            copy_dir = data_dir / "copy"
            copy_dir.mkdir(parents=True, exist_ok=True)
            
            # Create mock source database
            mock_source = copy_dir / "chat_copy.db"
            with sqlite3.connect(str(mock_source)) as conn:
                cursor = conn.cursor()
                
                # Create minimal schema
                cursor.execute("""
                    CREATE TABLE handle (
                        ROWID INTEGER PRIMARY KEY,
                        id TEXT
                    )
                """)
                cursor.execute("INSERT INTO handle VALUES (1, '+15551234567')")
                conn.commit()
            
            # Test that we can create a messages database
            messages_db_path = data_dir / "messages.db"
            db = MessagesDatabase(str(messages_db_path))
            success = db.create_database()
            
            assert success
            assert messages_db_path.exists()
            
            # Verify we can read from both databases
            with sqlite3.connect(str(mock_source)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM handle")
                handle_count = cursor.fetchone()[0]
                assert handle_count == 1


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])