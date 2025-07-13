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
    @echo "  just test       - Run all tests (pytest if available, unittest fallback)"
    @echo "  just test-unit  - Run tests with unittest"
    @echo "  just test-install - Install testing dependencies"
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
    @if command -v pytest >/dev/null 2>&1; then \
        echo "Using pytest..."; \
        python -m pytest tests/ -v; \
    else \
        echo "pytest not found, using unittest..."; \
        echo "To install pytest: pip install -r requirements.txt"; \
        python -m unittest discover tests/ -v; \
    fi

# Run tests with unittest (fallback option)
test-unit:
    @echo "🧪 Running tests with unittest..."
    python -m unittest discover tests/ -v

# Install testing dependencies
test-install:
    @echo "📦 Installing testing dependencies..."
    pip install pytest>=7.0.0 pytest-cov>=4.0.0 pytest-xdist>=3.0.0

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
    @echo "Chat Copy Database:" && ([ -f "./data/copy/chat_copy.db" ] && echo "  Present" || echo "  Not found")
    @echo "Messages Database:" && ([ -f "./data/messages.db" ] && echo "  Present" || echo "  Not found")