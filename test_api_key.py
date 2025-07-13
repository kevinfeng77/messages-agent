#!/usr/bin/env python3
"""Quick test script to verify Anthropic API key is working."""

import os
import sys
sys.path.append('src')

# Load .env file for local development
from load_env import load_env
load_env()

from message_maker.llm_client import LLMClient
from message_maker.types import LLMPromptData, ChatMessage, NewMessage

def test_api_key():
    """Test if API key is properly configured and working."""
    
    # Check if API key is available
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return False
    
    try:
        # Create client
        client = LLMClient()
        print("✅ LLM client initialized successfully")
        
        # Create test data
        chat_history = [
            ChatMessage("Hey, how's your day going?", True, "2023-01-01T10:00:00Z"),
            ChatMessage("Pretty good! Just working on some coding projects.", False, "2023-01-01T10:05:00Z")
        ]
        new_message = NewMessage("What kind of projects are you working on?", "2023-01-01T10:10:00Z")
        
        prompt_data = LLMPromptData(
            system_prompt="Test system prompt",
            user_prompt="Test user prompt", 
            chat_history=chat_history,
            new_message=new_message
        )
        
        print("🔄 Testing API call...")
        response = client.generate_responses(prompt_data)
        
        print("✅ API call successful!")
        print(f"Response 1: {response.response_1}")
        print(f"Response 2: {response.response_2}")
        print(f"Response 3: {response.response_3}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Anthropic API key configuration...\n")
    success = test_api_key()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")