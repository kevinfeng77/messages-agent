#!/usr/bin/env python3
"""
Demo script for iMessage Integration System

This script demonstrates the key features of the iMessage integration:
- Smart response suggestions based on conversation context
- Conversation analysis and pattern recognition
- Response generation for different scenarios
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.imessage.integration_manager import create_imessage_integration
from src.imessage.response_generator import ResponseSuggestion


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_suggestions(suggestions: List[ResponseSuggestion], title: str = "Response Suggestions"):
    """Print formatted response suggestions"""
    print(f"\n{title}:")
    if not suggestions:
        print("  No suggestions available")
        return
    
    for i, suggestion in enumerate(suggestions, 1):
        confidence_bar = "█" * int(suggestion.confidence * 10)
        print(f"  {i}. \"{suggestion.text}\"")
        print(f"     Confidence: {suggestion.confidence:.2f} {confidence_bar}")
        print(f"     Category: {suggestion.category}")
        if suggestion.reasoning:
            print(f"     Reasoning: {suggestion.reasoning}")
        print()


def demo_conversation_analysis(manager, conversations):
    """Demonstrate conversation analysis capabilities"""
    print_header("Conversation Analysis Demo")
    
    if not conversations:
        print("No conversations available for analysis demo")
        return
    
    # Analyze the first few conversations
    for i, conv in enumerate(conversations[:3]):
        handle_id = conv["handle_id"]
        display_name = conv.get("display_name", f"Handle {handle_id}")
        
        print(f"\nAnalyzing conversation with {display_name} (Handle ID: {handle_id})")
        print("-" * 50)
        
        # Get conversation context
        context = manager.conversation_analyzer.get_conversation_context(handle_id)
        if context:
            print(f"  Messages analyzed: {context.conversation_length}")
            print(f"  Conversation tone: {context.conversation_tone}")
            print(f"  Topic keywords: {', '.join(context.topic_keywords) if context.topic_keywords else 'None'}")
            print(f"  User last spoke: {context.user_last_spoke}")
            
            if context.time_since_last_message:
                hours = context.time_since_last_message.total_seconds() / 3600
                print(f"  Time since last message: {hours:.1f} hours")
            
            # Show some recent messages
            if context.recent_messages:
                print(f"  Recent messages (last 3):")
                for msg in context.recent_messages[-3:]:
                    sender = "You" if msg["is_from_me"] else display_name
                    print(f"    {sender}: \"{msg['text'][:50]}{'...' if len(msg['text']) > 50 else ''}\"")
        else:
            print("  No conversation context available")


def demo_response_generation(manager, conversations):
    """Demonstrate response suggestion generation"""
    print_header("Response Generation Demo")
    
    if not conversations:
        print("No conversations available for response generation demo")
        return
    
    # Generate suggestions for first few conversations
    for i, conv in enumerate(conversations[:3]):
        handle_id = conv["handle_id"]
        display_name = conv.get("display_name", f"Handle {handle_id}")
        
        print(f"\nGenerating suggestions for {display_name} (Handle ID: {handle_id})")
        print("-" * 50)
        
        # Get response suggestions
        suggestions = manager.get_response_suggestions_by_handle(handle_id, 3)
        print_suggestions(suggestions)


def demo_simulation_scenarios(manager):
    """Demonstrate response suggestions for various incoming message scenarios"""
    print_header("Message Simulation Demo")
    
    # Test various incoming message scenarios
    scenarios = [
        ("Thanks for your help today!", "Gratitude response"),
        ("What time should we meet tomorrow?", "Time/scheduling question"),
        ("Sorry I'm running late", "Apology acknowledgment"),
        ("Are you free for lunch?", "Social invitation"),
        ("Can you send me that document?", "Request response"),
        ("How was your weekend?", "Casual conversation"),
        ("Let me know when you're available", "Coordination response")
    ]
    
    print("Testing response suggestions for various message types:\n")
    
    for incoming_message, scenario_type in scenarios:
        print(f"Scenario: {scenario_type}")
        print(f"Incoming message: \"{incoming_message}\"")
        
        # Create a mock conversation analyzer for simulation
        from src.imessage.conversation_analyzer import ConversationContext
        from datetime import datetime, timedelta
        
        mock_context = ConversationContext(
            handle_id=999,
            recent_messages=[{"text": incoming_message, "is_from_me": False, "date": 1000000000}],
            conversation_length=5,
            last_message_time=datetime.now() - timedelta(minutes=5),
            user_last_spoke=False,
            contact_last_spoke=True,
            time_since_last_message=timedelta(minutes=5),
            conversation_tone="neutral"
        )
        
        # Generate suggestions using the response generator directly
        suggestions = manager.response_generator._get_context_based_suggestions(mock_context)
        pattern_suggestions = manager.response_generator._get_pattern_based_suggestions(mock_context)
        
        # Combine and enhance suggestions
        all_suggestions = suggestions + pattern_suggestions
        enhanced_suggestions = manager._enhance_suggestions_for_message(all_suggestions, incoming_message)
        
        # Get top 3 unique suggestions
        unique_suggestions = {}
        for suggestion in enhanced_suggestions:
            if suggestion.text not in unique_suggestions:
                unique_suggestions[suggestion.text] = suggestion
        
        top_suggestions = sorted(unique_suggestions.values(), key=lambda x: x.confidence, reverse=True)[:3]
        print_suggestions(top_suggestions, "Suggested responses")
        print("-" * 50)


def demo_system_status(manager):
    """Demonstrate system status and capabilities"""
    print_header("System Status and Capabilities")
    
    status = manager.get_system_status()
    
    print("System Status:")
    print(f"  Database connected: {'✓' if status.get('database_connected') else '✗'}")
    print(f"  System ready: {'✓' if status.get('system_ready') else '✗'}")
    
    if "database_stats" in status:
        stats = status["database_stats"]
        print(f"  Total messages: {stats.get('message_count', 'Unknown')}")
        print(f"  Contacts: {stats.get('contact_count', 'Unknown')}")
        print(f"  Database size: {stats.get('database_size', 0) / 1024 / 1024:.1f} MB")
    
    print(f"  Recent conversations: {status.get('recent_conversations_count', 'Unknown')}")
    
    if status.get("last_database_update"):
        print(f"  Last database update: {status['last_database_update']}")


def main():
    """Main demo function"""
    print_header("iMessage Integration System Demo")
    print("This demo showcases the smart response suggestion system for iMessage")
    
    try:
        # Initialize the integration manager
        print("\nInitializing iMessage Integration Manager...")
        manager = create_imessage_integration()
        print("✓ Integration manager initialized successfully")
        
        # Get recent conversations for demos
        print("\nFetching recent conversations...")
        conversations = manager.get_recent_conversations(10)
        print(f"✓ Found {len(conversations)} recent conversations")
        
        # Demo 1: System status
        demo_system_status(manager)
        
        # Demo 2: Conversation analysis
        demo_conversation_analysis(manager, conversations)
        
        # Demo 3: Response generation
        demo_response_generation(manager, conversations)
        
        # Demo 4: Message simulation scenarios
        demo_simulation_scenarios(manager)
        
        # Cleanup
        manager.cleanup()
        
        print_header("Demo Complete")
        print("The iMessage integration system is ready for use!")
        print("\nKey Features Demonstrated:")
        print("  ✓ Conversation context analysis")
        print("  ✓ Smart response suggestion generation")
        print("  ✓ Pattern-based and context-aware suggestions")
        print("  ✓ Multiple suggestion strategies")
        print("  ✓ Performance monitoring and validation")
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        print("Please ensure the Messages database is accessible and try again.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)