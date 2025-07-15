#!/usr/bin/env python3
"""Binary search to find maximum chat history size that works with API."""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.message_maker.chat_history import get_chat_history_for_message_generation
from src.message_maker.api import MessageMakerService
from src.message_maker.types import MessageRequest, LLMPromptData, NewMessage
from datetime import datetime

def test_message_limit(limit: int, request: MessageRequest) -> bool:
    """Test if a specific message limit works with the API."""
    print(f"Testing limit: {limit} messages...")
    
    try:
        # Get chat history
        chat_history = get_chat_history_for_message_generation(
            chat_id=str(request.chat_id),
            user_id=request.user_id
        )
        
        # Limit to recent messages
        if len(chat_history) > limit:
            chat_history = chat_history[-limit:]
        
        print(f"  Using {len(chat_history)} messages")
        
        # Calculate total characters
        total_chars = sum(len(msg.contents) for msg in chat_history)
        print(f"  Total characters: {total_chars:,}")
        
        # Create service and test
        service = MessageMakerService()
        
        # Prepare LLM prompt
        new_message = NewMessage(
            contents=request.contents,
            created_at=datetime.now().isoformat()
        )
        
        prompt_data = LLMPromptData(
            system_prompt="placeholder",
            user_prompt="placeholder",
            chat_history=chat_history,
            new_message=new_message
        )
        
        # Try to generate responses
        response = service.llm_client.generate_responses(prompt_data)
        print(f"  ✅ SUCCESS! Generated {len(response.get_responses())} responses")
        return True
        
    except Exception as e:
        error_str = str(e)
        if '529' in error_str or 'overloaded' in error_str.lower():
            print(f"  ❌ FAILED: API Overloaded")
            return False
        elif 'token' in error_str.lower() or 'length' in error_str.lower():
            print(f"  ❌ FAILED: Token/Length limit - {e}")
            return False
        else:
            print(f"  ❌ FAILED: Other error - {e}")
            return False

def binary_search_max_limit(request: MessageRequest, max_limit: int = 10000) -> int:
    """Binary search to find maximum working message limit."""
    print(f"Starting binary search for max message limit (up to {max_limit})...")
    
    low = 1
    high = max_limit
    best_working = 0
    
    while low <= high:
        mid = (low + high) // 2
        print(f"\nTrying {mid} messages (range: {low}-{high})...")
        
        if test_message_limit(mid, request):
            best_working = mid
            low = mid + 1
            print(f"  ✅ {mid} works! Trying higher...")
            # Brief pause to avoid hitting API too hard
            time.sleep(2)
        else:
            high = mid - 1
            print(f"  ❌ {mid} failed! Trying lower...")
            # Brief pause for API recovery
            time.sleep(3)
    
    return best_working

def main():
    """Main test function."""
    request = MessageRequest(
        chat_id=2,
        user_id='f8863561-0ecd-4e90-8372-56639ea117c4',
        contents='do you even love me'
    )
    
    print("=" * 60)
    print("BINARY SEARCH FOR MAXIMUM MESSAGE LIMIT")
    print("=" * 60)
    
    # Start with a few quick tests
    print("\nQuick tests first...")
    
    # Test very small number first
    if not test_message_limit(10, request):
        print("❌ Even 10 messages failed! API may be completely overloaded.")
        return
    
    time.sleep(2)
    
    # Test medium number
    if not test_message_limit(100, request):
        print("100 messages failed, starting binary search from 1-99...")
        max_limit = binary_search_max_limit(request, 99)
    else:
        print("100 messages worked! Testing higher...")
        time.sleep(2)
        
        # Binary search from 100 to 10000
        max_limit = binary_search_max_limit(request, 10000)
    
    print("\n" + "=" * 60)
    print(f"RESULT: Maximum working limit is {max_limit} messages")
    print("=" * 60)
    
    if max_limit > 0:
        print(f"\nTesting final result with {max_limit} messages...")
        success = test_message_limit(max_limit, request)
        if success:
            print("✅ Final test confirmed!")
        else:
            print("❌ Final test failed - may need to reduce slightly")

if __name__ == "__main__":
    main()