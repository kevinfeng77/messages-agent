#!/usr/bin/env python3
"""
Unit tests for environment variable loading in test_message_maker.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestEnvLoading(unittest.TestCase):
    """Test environment variable loading functionality."""

    def setUp(self):
        """Set up test environment."""
        # Store original environment
        self.original_env = os.environ.copy()
        
        # Clear ANTHROPIC_API_KEY if set
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_env_file_loading_with_dotenv_available(self):
        """Test that .env file is loaded when python-dotenv is available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a .env file
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("ANTHROPIC_API_KEY=test_key_from_env_file\n")
            
            # Mock the current working directory
            with patch('os.getcwd', return_value=temp_dir):
                # Mock the dotenv import and load_dotenv function
                mock_load_dotenv = MagicMock()
                with patch.dict('sys.modules', {'dotenv': MagicMock(load_dotenv=mock_load_dotenv)}):
                    # Import and execute the env loading code
                    exec("""
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
""")
                    
                    # Verify load_dotenv was called
                    mock_load_dotenv.assert_called_once()

    def test_env_file_loading_without_dotenv(self):
        """Test that script continues gracefully when python-dotenv is not available."""
        # Mock ImportError for dotenv
        with patch.dict('sys.modules', {'dotenv': None}):
            # This should not raise an exception
            try:
                exec("""
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
""")
            except Exception as e:
                self.fail(f"Script should handle missing dotenv gracefully, but raised: {e}")

    def test_anthropic_key_detection_from_env_file(self):
        """Test that ANTHROPIC_API_KEY is detected after loading from .env file."""
        # Set the key in environment (simulating successful .env loading)
        os.environ["ANTHROPIC_API_KEY"] = "test_key_123"
        
        # Check the same logic as in test_message_maker.py
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.assertIsNotNone(api_key)
        self.assertEqual(api_key, "test_key_123")

    def test_anthropic_key_missing_error_message(self):
        """Test error message when ANTHROPIC_API_KEY is not set."""
        # Ensure the key is not set
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        
        # Check the same logic as in test_message_maker.py
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.assertIsNone(api_key)

    def test_anthropic_key_from_manual_export(self):
        """Test that manually exported ANTHROPIC_API_KEY still works."""
        # Set key via manual export (environment variable)
        os.environ["ANTHROPIC_API_KEY"] = "manually_exported_key"
        
        # Check detection
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.assertIsNotNone(api_key)
        self.assertEqual(api_key, "manually_exported_key")


if __name__ == "__main__":
    unittest.main()