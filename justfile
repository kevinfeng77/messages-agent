# Messages Agent Setup Commands
# 
# This justfile provides convenient commands for setting up the Messages Agent system.
# Run `just setup` to perform complete database setup from scratch.

# Default recipe shows available commands
default:
    @echo "Available commands:"
    @echo "  just setup      - Complete database setup from clean state"
    @echo "  just copy       - Copy Messages database only"
    @echo "  just create     - Create and populate messages.db only"
    @echo "  just clean      - Clean data directory"
    @echo "  just test       - Run all tests"
    @echo "  just validate   - Run validation scripts"

# Complete setup: clean data, copy database, create and populate messages.db
setup: clean copy create
    @echo ""
    @echo "🎉 Complete setup finished! Both databases are ready:"
    @echo "   - data/copy/chat_copy.db (Messages database copy)"
    @echo "   - data/messages.db (Normalized database with full data)"

# Copy Messages database to working directory
copy:
    @echo "📋 Copying Messages database..."
    python scripts/copy_messages_database.py

# Create and populate the messages.db database
create:
    @echo "🗄️ Creating and populating messages database..."
    python scripts/setup_messages_database.py

# Clean the data directory 
clean:
    @echo "🧹 Cleaning data directory..."
    rm -rf data/
    mkdir -p data/copy
    @echo "✅ Data directory cleaned and recreated"

# Run all tests
test:
    @echo "🧪 Running all tests..."
    python -m pytest tests/ -v

# Run validation scripts
validate:
    @echo "✅ Running validation scripts..."
    python scripts/validation/validate_messages_table.py
    python scripts/validation/validate_chat_migration.py

# Development helpers
lint:
    @echo "🔍 Running code quality checks..."
    black --check scripts/ src/
    isort --check-only scripts/ src/
    flake8 scripts/ src/
    mypy src/

format:
    @echo "📝 Formatting code..."
    black scripts/ src/
    isort scripts/ src/

# Show database statistics
stats:
    @echo "📊 Database statistics:"
    @python3 -c "
import sqlite3
from pathlib import Path

for db_name, db_path in [('Chat Copy', './data/copy/chat_copy.db'), ('Messages', './data/messages.db')]:
    if Path(db_path).exists():
        print(f'\\n{db_name} Database ({db_path}):')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if db_name == 'Chat Copy':
            cursor.execute('SELECT COUNT(*) FROM message')
            print(f'  Messages: {cursor.fetchone()[0]:,}')
            cursor.execute('SELECT COUNT(*) FROM chat')  
            print(f'  Chats: {cursor.fetchone()[0]:,}')
            cursor.execute('SELECT COUNT(*) FROM handle')
            print(f'  Handles: {cursor.fetchone()[0]:,}')
        else:
            tables = ['users', 'chats', 'messages', 'chat_users', 'chat_messages']
            for table in tables:
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    count = cursor.fetchone()[0]
                    print(f'  {table.title()}: {count:,}')
                except:
                    print(f'  {table.title()}: N/A')
        
        conn.close()
    else:
        print(f'\\n{db_name} Database: Not found')
"