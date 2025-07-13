#!/usr/bin/env python3
"""Load environment variables from .env file for local development."""

import os
from pathlib import Path

def load_env():
    """Load environment variables from .env file if it exists."""
    env_file = Path(__file__).parent / '.env'
    
    if not env_file.exists():
        print(f"⚠️  No .env file found at {env_file}")
        return
    
    try:
        # Try using python-dotenv if available
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print("✅ Environment variables loaded using python-dotenv")
    except ImportError:
        # Fallback to manual parsing
        print(f"Loading environment variables from {env_file} (manual parsing)")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip().strip('"').strip("'")
                    os.environ[key.strip()] = value
        print("✅ Environment variables loaded")

if __name__ == "__main__":
    load_env()