# Message Agent Project - Claude Instructions

## CRITICAL: Always Create Feature Branch First

**MANDATORY FIRST STEP for ANY Linear ticket work:**

### Standard Workflow: Git Worktree (MANDATORY)
Before implementing ANY Linear ticket, you MUST create a new worktree:

1. **Ensure main repository has latest changes:**
   ```bash
   # From main repository directory
   git checkout main
   git pull origin main
   ```

2. **Create new worktree with feature branch from latest main:**
   ```bash
   # IMPORTANT: Create worktrees as subdirectories, not sibling directories
   # This avoids Claude Code security restrictions on directory access
   mkdir -p worktrees
   git worktree add worktrees/{ticket-description} -b ${USER}/{description-of-changes}
   cd worktrees/{ticket-description}
   ```

### Alternative: Traditional Branch Workflow (Only if worktrees unavailable)
If git worktrees are not available, fall back to standard branching:

1. **Switch to main and pull latest changes:**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create new feature branch from latest main:**
   ```bash
   git checkout -b ${USER}/{description-of-changes}
   ```

3. **List and manage worktrees:**
   ```bash
   git worktree list                           # Show all worktrees
   git worktree remove worktrees/{name}        # Remove completed worktree
   git worktree prune                         # Clean up stale worktree metadata
   ```

**Worktree Benefits:**
- Work on multiple tickets simultaneously without context switching
- Isolate development environments
- Run tests in parallel
- Review PRs in separate directories

**Example worktree names (CORRECTED):**
- `worktrees/message-maker-data-classes`
- `worktrees/neo4j-setup`
- `worktrees/pr-review`

**Example branch names:**
- `${USER}/message-maker-structure-fix`
- `${USER}/person-entity-schema`
- `${USER}/neo4j-setup`

**NEVER work directly on main or existing branches for new tickets - this step is NON-NEGOTIABLE.**


## Linear Integration Workflow

### Automatic Plan Generation
When a user provides a Linear ticket link (e.g., `https://linear.app/serene-ai/issue/SERENE-XX/...`):

1. **Extract ticket information** using the Linear MCP server
2. **Analyze the task context** within the broader Message Agent architecture
3. **Generate a detailed implementation plan** automatically
4. **Present the plan** for review and refinement

### Plan Generation Instructions

When you receive a Linear ticket link or ID:

```markdown
## Auto-Plan Generation Protocol

1. **Extract Ticket ID**
   - From URL format `https://linear.app/serene-ai/issue/SERENE-XX/...` extract "SERENE-XX"
   - Accept direct ticket IDs like "SERENE-46" as well

2. **Fetch Ticket Details**
   - Use `mcp__linear__get_issue` with the extracted ticket ID
   - Example: `mcp__linear__get_issue(id="SERENE-46")`
   - **CRITICAL ERROR HANDLING**: 
     - If Linear MCP server is unavailable: STOP and inform user
     - If ticket ID is invalid/not found: STOP and inform user
     - If authentication fails: STOP and inform user
     - If any other access error occurs: STOP and inform user
   - **DO NOT PROCEED** without successful ticket access
   - Request user to provide ticket details manually if access fails
   - Extract: title, description, estimate, priority, project context

3. **Analyze Technical Context**
   - Identify which phase/component this task belongs to
   - Review related database schemas and existing codebase
   - Consider dependencies and integration points

4. **Generate Implementation Plan**
   - Break down into 3-7 concrete steps
   - Include technical approach and architecture decisions
   - Specify files to create/modify
   - Identify testing requirements
   - Note any dependencies or blockers

5. **Present Plan Structure**
   ```
   # Implementation Plan: [Task Title]
   
   ## Overview
   [Brief summary of what we're building and why]
   
   ## Technical Approach
   [Architecture decisions, patterns, libraries to use]
   
   ## Implementation Steps
   1. [Step 1 with specific files/actions]
   2. [Step 2 with specific files/actions]
   ...
   
   ## Testing Strategy
   [How to validate the implementation]
   
   ## Dependencies & Integration
   [What this connects to, blockers, prerequisites]
   
   ## Success Criteria
   [Definition of done]
   ```

6. **Create Feature Branch**
   - ALWAYS create a new branch for each Linear ticket
   - Use naming convention: `${USER}/{ticket-description}`
   - Branch from main/master before starting implementation
   - Example: `git checkout -b ${USER}/refactor-directory-tree`

7. **Await Confirmation**
   - Present plan for review
   - Allow for modifications and refinement
   - Proceed with implementation once approved

8. **Implementation Completion**
   - Always create comprehensive test suite
   - Run validation scripts
   - Create PR automatically using GitHub MCP
   - Include performance metrics and validation results

9. **Adhere Strictly to Specifications**
   - **ONLY implement what is specified** in the Linear ticket
   - Write minimal, concise code that satisfies the exact requirements
   - **DO NOT add extra features, optimizations, or functionality** beyond the scope
   - Focus on meeting the defined success criteria, nothing more
```

## Project Context & Architecture

**Current System Status:**
This is a **functional AI messaging assistant** with complete message processing, AI response generation, and live polling capabilities. The system is operational and actively used for intelligent message responses.

### Technology Stack
- **Backend**: Python 3.11+ with asyncio for concurrent operations
- **Database**: SQLite with normalized schema (users, chats, messages, relationships)
- **AI/ML**: Anthropic Claude API for response generation, Graphiti framework for knowledge graphs
- **Message Processing**: AppleScript integration with Messages.app, binary text decoding
- **Infrastructure**: Local processing with comprehensive logging and validation

### Current Codebase Structure
```
messages-agent/
├── main.py                      # 🚀 Interactive AI response generation workflow
├── polling_main.py              # 📱 Real-time message polling with notifications
├── src/
│   ├── database/
│   │   ├── manager.py           # Original Messages.app database copying
│   │   ├── messages_db.py       # ✅ Normalized database with users/chats/messages
│   │   ├── migrator.py          # Database migration utilities
│   │   ├── message_migration.py # Message text decoding from binary
│   │   ├── polling_service.py   # ✅ Live message polling service
│   │   ├── smart_manager.py     # Smart database copy management
│   │   └── tests/               # Database tests
│   ├── message_maker/
│   │   ├── api.py               # ✅ AI response generation API
│   │   ├── chat_history.py      # Chat context retrieval
│   │   ├── llm_client.py        # Claude API integration
│   │   └── types.py             # Message request/response types
│   ├── messaging/
│   │   ├── decoder.py           # ✅ Binary message text decoding
│   │   ├── service.py           # ✅ Message sending via AppleScript
│   │   ├── config.py            # Messaging configuration
│   │   ├── applescript_service.py # AppleScript integration
│   │   └── exceptions.py        # Messaging exceptions
│   ├── user/
│   │   ├── user.py              # User data model
│   │   ├── service.py           # User lookup and phone number formatting
│   │   ├── handle_matcher.py    # Handle ID to user mapping
│   │   └── tests/               # User service tests
│   ├── extractors/
│   │   ├── addressbook_extractor.py # Contact data extraction
│   │   └── tests/
│   ├── graphiti/                # 🔄 Knowledge graph framework (ready for integration)
│   │   ├── episode_manager.py   # Graphiti episode management
│   │   ├── query_manager.py     # Graph query utilities
│   │   └── example_script.py    # Usage examples
│   └── utils/
│       ├── logger_config.py     # Centralized logging
│       └── load_env.py          # Environment variable loading
├── scripts/                     # 🛠️ Organized utility scripts
│   ├── copy_messages_database.py    # Copy Messages.app database
│   ├── setup_messages_database.py  # Setup normalized database
│   ├── migration/               # Database schema migrations
│   ├── validation/              # ✅ Comprehensive validation scripts
│   │   ├── validate_live_polling.py     # Live polling validation
│   │   ├── validate_message_maker.py    # AI response validation
│   │   ├── validate_message_sending.py  # Message sending validation
│   │   └── [12+ other validation scripts]
│   └── debug/                   # Debugging utilities
├── tests/                       # 🧪 Comprehensive test suite (321+ tests)
│   ├── integration/             # Integration tests
│   ├── unit/                    # Unit tests by module
│   │   ├── database/           # Database layer tests
│   │   ├── user/               # User service tests
│   │   └── extractors/         # Extractor tests
│   └── [25+ test files]        # Core functionality tests
├── data/                        # Generated databases and logs
│   ├── copy/                   # Messages.app database copy
│   ├── messages.db             # ✅ Normalized database
│   └── [log files]
├── justfile                     # ⚡ Task runner with 10+ commands
├── CLAUDE.md                    # 📋 AI assistant instructions
└── requirements.txt             # Python dependencies
```

**Key Operational Files:**
- **`main.py`**: Complete AI response workflow (input → AI suggestions → send)
- **`polling_main.py`**: Real-time message monitoring with notifications
- **`src/message_maker/api.py`**: Core AI response generation
- **`src/database/polling_service.py`**: Live message detection
- **`src/messaging/service.py`**: Automated message sending

### Key Design Principles
- **Privacy First**: All processing local, no external data sharing, Messages.app database copied safely
- **Operational Excellence**: Working AI response system with 321+ tests, comprehensive validation
- **Real-time Capabilities**: Live message polling, instant notifications, sub-second response times
- **Modular Architecture**: Clean separation between database, AI, messaging, and user layers
- **Developer Experience**: Simple setup (`just setup`), extensive testing, organized scripts

## Common Patterns & Guidelines

### For Database Tasks
- Use `MessagesDatabase` class from `src/database/messages_db.py` for normalized operations
- Use `MessagePollingService` for live message detection and processing
- Follow existing patterns in `src/database/manager.py` for Messages.app database copying
- Implement proper error handling and logging using `src/utils/logger_config.py`
- Write comprehensive tests for data operations (see `tests/unit/database/`)

### For AI Response Generation
- Use `generate_message_responses()` from `src/message_maker/api.py`
- Build `MessageRequest` objects with chat_id, user_id, and contents
- Configure context limits appropriately (default: 200 messages)
- Handle AI API errors gracefully with fallback responses
- Test with various message types and edge cases

### For Message Processing
- Use `MessageService` from `src/messaging/service.py` for sending messages
- Apply text decoding with `src/messaging/decoder.py` for binary message content
- Configure AppleScript permissions properly for Messages.app integration
- Format phone numbers using `UserService.format_phone_number()`
- Test message sending with various recipient formats

### For Live Polling
- Use `MessagePollingService` with appropriate poll intervals (1-5 seconds)
- Implement proper callback functions for new message notifications
- Handle database copy freshness and automatic refreshing
- Monitor performance metrics and optimize batch sizes
- Test with high-frequency message scenarios

### For Graphiti Integration (Future)
- Design minimal episodes with clear temporal boundaries
- Let Graphiti extract relationships and facts
- Implement proper error handling for graph operations
- Include monitoring for graph query performance

### For Testing (MANDATORY)
**ALWAYS Required for Every Implementation:**
- **Unit Tests**: Test all new functions, classes, and methods
- **Integration Tests**: Test database operations and external dependencies
- **Performance Tests**: Test with realistic data volumes (especially for data processing)
- **Validation Scripts**: Create end-to-end validation for major features
- **Error Handling Tests**: Test edge cases and failure scenarios
- **Regression Tests**: Ensure existing functionality still works

**Testing Requirements:**
- Minimum 100% code coverage for new code
- All tests must pass before PR creation (`just test` should show 321+ passing tests)
- Include both positive and negative test cases
- Test with real data samples when available
- Use existing test patterns from current 25+ test files
- Document test approach in implementation plan

**Current Test Organization:**
```
tests/
├── unit/                        # 🧪 Unit tests (isolated components)
│   ├── database/               # Database layer tests
│   ├── user/                   # User service tests  
│   ├── extractors/             # Data extraction tests
│   └── test_[module].py        # Individual module tests
├── integration/                 # 🔄 Integration tests (cross-component)
│   └── test_[feature]_integration.py
├── test_[feature].py           # 📋 Feature-level tests (25+ files)
│   ├── test_api.py             # AI response generation
│   ├── test_live_polling_integration.py  # Live polling
│   ├── test_message_decoder.py # Text decoding
│   ├── test_messaging_service.py # Message sending
│   └── [21+ other test files]
└── scripts/validation/         # ✅ End-to-end validation
    ├── validate_live_polling.py
    ├── validate_message_maker.py
    └── [12+ validation scripts]
```

**Test Running:**
- `just test` - Run all tests (currently 321+ passing)
- Individual test files can be run with pytest
- Tests use realistic data patterns and comprehensive mocking
- Both unit and integration tests validate core functionality

### For Script Organization (MANDATORY)
**All scripts must be organized into proper subdirectories:**
- **Migration Scripts**: Place in `scripts/migration/` directory
- **Validation Scripts**: Place in `scripts/validation/` directory
- **Debug Scripts**: Place in `scripts/debug/` directory
- **Main Orchestration Scripts**: Keep in root `scripts/` directory

**Script Organization Rules:**
- Migration scripts handle database schema changes and data migration
- Validation scripts verify implementation correctness and test specific requirements
- Debug scripts provide diagnostic and troubleshooting capabilities
- Never leave migration or validation scripts in the root scripts directory
- Update import paths when moving scripts to subdirectories
- Update README files in each subdirectory to document new scripts

## Git Workflow & Branch Management

### Branch Naming Convention
All branches should follow the pattern: `${USER}/{description-of-changes-in-few-words}`

**Examples:**
- `${USER}/person-entity-schema`
- `${USER}/neo4j-setup`
- `${USER}/message-validation`
- `${USER}/response-generation-api`

### Pull Request Guidelines

**PR Title Format:** `[LINEAR-TICKET-NUMBER] Quick description`

**Examples:**
- `[SERENE-11] Create Person entity schema definition`
- `[SERENE-27] Set up Neo4j development environment`
- `[SERENE-35] Design batch processing chunking strategy`

**PR Process:**
1. **Create Feature Branch**
   ```bash
   # Switch to main and pull latest changes
   git checkout main
   git pull origin main
   
   # Create new feature branch from latest main
   git checkout -b ${USER}/{short-description}
   ```

2. **Implement Changes**
   - Follow the implementation plan
   - Include tests and documentation
   - Run linting and quality checks

3. **Create Pull Request (Use GitHub MCP)**
   - **ALWAYS use GitHub MCP tools** instead of external CLI tools
   - Use `mcp__github__create_pull_request` with proper parameters
   - Include comprehensive PR description with metrics and validation
   - Link to Linear ticket in description
   - Use proper title format with Linear ticket number

4. **Enhanced PR Template**
   ```markdown
   ## Summary
   [Brief description of changes and impact]

   ## Linear Ticket
   Closes [Linear ticket URL]

   ## Problem Solved
   [Specific problem this addresses with context]

   ## Implementation Details
   - [Key implementation points]
   - [Architecture decisions made]
   - [Performance considerations]

   ## Results Achieved
   ### Performance Metrics
   - [Quantifiable improvements, if applicable]
   - [Processing speed, accuracy, coverage, etc.]
   
   ### Validation Results
   - [Validation script results]
   - [Success criteria met]

   ## Testing (MANDATORY)
   - [ ] **Unit tests**: Created for all new functions/classes
   - [ ] **Integration tests**: Database and external dependencies tested
   - [ ] **Performance tests**: Tested with realistic data volumes
   - [ ] **Validation script**: End-to-end validation implemented
   - [ ] **Error handling**: Edge cases and failures tested
   - [ ] **Test coverage**: ≥80% coverage achieved
   - [ ] **All tests passing**: Full test suite executed successfully

   ## Architecture & Security
   - [ ] Code follows project conventions
   - [ ] Documentation updated
   - [ ] No breaking changes (or properly documented)
   - [ ] Comprehensive logging and error handling
   - [ ] Security considerations addressed
   - [ ] Performance impact assessed

   ## Impact
   [Overall impact and value delivered]
   ```

## Commands & Scripts

### Development Commands
```bash
# Complete setup from clean state
just setup

# Install dependencies  
pip install -r requirements.txt

# Run tests (321+ tests)
just test

# Run validation scripts
just validate

# Code quality
just lint       # Run linting checks
just format     # Format code with black/isort

# Database operations
just copy       # Copy Messages.app database
just create     # Create normalized database
just clean      # Clean data directory
just stats      # Show database statistics

# Main workflows
python main.py          # Interactive AI response generation
python polling_main.py  # Real-time message polling with notifications
```

### Git Commands
```bash
# Switch to main and pull latest changes
git checkout main
git pull origin main

# Create and switch to feature branch from latest main
git checkout -b ${USER}/{description}

# Add and commit changes
git add .
git commit -m "Implement [feature description]"

# Push branch (PR creation handled by MCP)
git push -u origin ${USER}/{description}

# After PR approval, clean up
git checkout main
git pull origin main
git branch -d ${USER}/{description}
```

### Git Worktrees for Parallel Development

**Git worktrees enable working on multiple branches simultaneously without stashing or switching contexts.**

#### When to Use Git Worktrees
- **Hotfix Development**: Work on urgent fixes while maintaining progress on feature branches
- **Code Reviews**: Check out PR branches in separate directories for IDE-based review
- **Experimentation**: Test new approaches without disrupting main development workflow
- **Parallel Features**: Develop multiple features concurrently without context switching

#### Worktree Management Commands
```bash
# List all worktrees
git worktree list

# Add worktree for existing branch (CORRECTED - use subdirectories)
git worktree add worktrees/feature-name feature-branch-name

# Add worktree and create new branch (CORRECTED - use subdirectories)
git worktree add -b ${USER}/new-feature worktrees/new-feature

# Add worktree for hotfix from main (CORRECTED - use subdirectories)
git worktree add -b ${USER}/hotfix-urgent worktrees/hotfix-urgent main

# Remove completed worktree (CORRECTED - use subdirectories)
git worktree remove worktrees/feature-name

# Clean up stale worktree metadata
git worktree prune
```

#### Recommended Directory Structure (CORRECTED)
```
message-agent/                          # Main repository directory
├── src/                               # Source code
├── worktrees/                         # Worktree subdirectories (CORRECTED)
│   ├── hotfix-urgent/                # Hotfix worktree
│   ├── pr-review/                    # PR review worktree  
│   ├── message-maker-data-classes/   # Feature worktree
│   └── experimental-feature/         # Experimental feature worktree
└── [other repository files]
```

**IMPORTANT SECURITY NOTE**: Claude Code restricts directory access to child directories only. Worktrees MUST be created as subdirectories (e.g., `worktrees/{name}`) rather than sibling directories (e.g., `../message-agent-{name}`) to avoid security restrictions.

#### Worktree Workflow Best Practices
1. **Consistent Naming**: Use `{purpose}` or `{ticket-description}` pattern for worktree subdirectories
2. **Regular Updates**: Keep worktrees synchronized with remote changes:
   ```bash
   # In each worktree directory
   git fetch origin
   git pull origin main  # or relevant base branch
   ```
3. **Clean Commits**: Always commit or stash changes before switching between worktrees
4. **Strategic Cleanup**: Remove worktrees promptly after branch merging to avoid clutter
5. **Branch Tracking**: Ensure each worktree branch tracks appropriate remote branch:
   ```bash
   git branch --set-upstream-to=origin/feature-branch
   ```

#### Advanced Worktree Workflows (CORRECTED)
```bash
# Create worktree for PR review (CORRECTED - use subdirectories)
git fetch origin pull/123/head:pr-123
git worktree add worktrees/pr-123 pr-123

# Cherry-pick commits between worktrees (CORRECTED - use subdirectories)
cd worktrees/feature-name
git cherry-pick <commit-hash-from-other-worktree>

# Create experimental worktree from current branch (CORRECTED - use subdirectories)
git worktree add -b ${USER}/experiment worktrees/experiment

# Worktree for database migration testing (CORRECTED - use subdirectories)
git worktree add -b ${USER}/migration-test worktrees/migration-test
```

#### Integration with Message Agent Development
- **Phase Development**: Use separate worktrees for each development phase
- **Database Testing**: Isolate database migration testing in dedicated worktrees  
- **Graphiti Experiments**: Test knowledge graph changes without affecting main development
- **API Development**: Parallel development of different API endpoints
- **Performance Testing**: Dedicated worktree for performance optimization work

### GitHub MCP Workflow (PREFERRED METHOD)
**ALWAYS use GitHub MCP tools instead of external CLI tools:**

```python
# Create Pull Request
mcp__github__create_pull_request(
    owner="kevinfeng77",
    repo="messages-agent", 
    title="[LINEAR-TICKET] Description",
    head="${USER}/{branch-name}",
    base="main",
    body="[Comprehensive PR description with metrics]"
)

# Other useful GitHub MCP tools:
# - mcp__github__get_file_contents: Read files from repo
# - mcp__github__push_files: Push multiple files at once
# - mcp__github__create_branch: Create branches
# - mcp__github__merge_pull_request: Merge PRs
```

**Benefits of Using GitHub MCP:**
- No external dependencies or CLI installation required
- Integrated authentication and error handling
- Consistent API interface across all operations
- Better error messages and debugging capabilities

### GitHub Actions & Branch Protection

**All PRs must pass automated tests before merging via GitHub Actions workflow.**

#### Required Status Checks
The repository uses a GitHub Actions workflow (`.github/workflows/test.yml`) that runs:

1. **Test Suite**: `just test` - Runs all unit and integration tests (321+ tests)
2. **Dependencies**: Automatic installation of testing dependencies

**Current Status**: Test suite is fully operational with 321+ passing tests. Code formatting and linting checks are available via `just lint` and `just format`.

#### Workflow Triggers
- **Pull Requests**: All PRs to `main` or `master` branches
- **Direct Pushes**: Commits pushed directly to `main` or `master`

#### Branch Protection Rules
Configure the following branch protection rules in GitHub repository settings:
- **Require status checks to pass**: Enable for the "Tests" workflow
- **Require branches to be up to date**: Ensure PRs include latest main changes
- **Include administrators**: Apply rules to repository administrators
- **Restrict pushes**: Only allow merges through pull requests

#### Workflow Configuration
```yaml
# .github/workflows/test.yml
name: Tests
on:
  pull_request:
    branches: [ main, master ]
  push:
    branches: [ main, master ]
```

**This ensures no code reaches main without:**
- ✅ All tests passing (`just test` - 321+ tests)

### Linting & Quality (MANDATORY BEFORE PR)
```bash
# Use Just commands for standardized quality checks
just lint       # Run flake8, mypy, and other linting tools
just format     # Format code with black and isort

# Manual commands (if needed)
black src/ tests/
isort src/ tests/
flake8 src/
mypy src/

# Verify all checks pass locally before pushing
just lint && just test
```

**MANDATORY Pre-Push Checks:**
- All tests must pass: `just test` (321+ tests)
- Code must be properly formatted: `just format`
- Linting checks must pass: `just lint`
- Never push code that fails local quality checks

## Current Implementation Status

**✅ Completed Core Features:**
- **Message Database Processing**: Complete extraction and normalization from Messages.app
- **AI Response Generation**: Interactive workflow with Claude API integration
- **Live Message Polling**: Real-time message detection with notifications
- **Message Sending**: AppleScript-based automated message sending
- **Comprehensive Testing**: 321+ tests with validation scripts


## Complete Implementation Workflow

### MANDATORY Implementation Steps (Always Follow):

1. **Plan Generation**
   - Fetch Linear ticket details using MCP
   - Generate detailed implementation plan
   - Include testing strategy and success criteria

2. **Branch Creation (MANDATORY)**
   - **ALWAYS create a new feature branch** for each Linear ticket
   - Use naming convention: `${USER}/{ticket-description}` (e.g., `${USER}/refactor-directory-tree`)
   - Create branch from main/master: `git checkout -b ${USER}/{description}`
   - Never work directly on main or existing branches for new tickets

3. **Implementation**
   - Implement core functionality on the feature branch
   - **ALWAYS write tests concurrently** (not after)
   - Include comprehensive error handling and logging

4. **Testing (REQUIRED)**
   - Create unit tests for all new functions/classes
   - Add integration tests for database/external dependencies
   - Build performance tests for data processing features
   - Create validation script for end-to-end testing
   - Ensure ≥80% code coverage
   - All tests must pass before proceeding

5. **Validation & Metrics**
   - Run validation script and collect metrics
   - Document performance improvements
   - Verify success criteria are met
   - Test edge cases and error conditions

6. **PR Creation (Use GitHub MCP) - MANDATORY**
   - **ALWAYS create PR when implementation checklist is completed**
   - Commit all changes with descriptive messages
   - Push branch to origin: `git push -u origin ${USER}/{branch-name}`
   - Use `mcp__github__create_pull_request` to create PR
   - Include comprehensive description with:
     - Problem statement and solution
     - Performance metrics and validation results  
     - Testing checklist (all items checked)
     - Impact and value delivered
   - **Remember**: PR creation is not optional - it's required for every completed ticket

7. **Documentation**
   - Update relevant documentation
   - Include architectural decisions
   - Document trade-offs and alternatives considered

### Testing Requirements (NON-NEGOTIABLE)
- **Unit Tests**: Every new function, class, method
- **Integration Tests**: Database operations, external APIs
- **Performance Tests**: Realistic data volumes, load testing
- **Validation Scripts**: End-to-end feature validation
- **Error Handling**: Edge cases, failure scenarios
- **Regression Tests**: Existing functionality preservation

### PR Requirements
- **Use GitHub MCP**: Never use external CLI tools
- **Comprehensive Description**: Include metrics, validation, impact
- **All Tests Passing**: 100% test success required
- **Code Coverage**: Minimum 80% for new code
- **Linear Link**: Always link to originating ticket
- **MANDATORY**: Always create PR when checklist is completed

## Notes for Claude

- **MANDATORY**: Always create comprehensive test suites
- **MANDATORY**: Use GitHub MCP for all GitHub operations
- **MANDATORY**: Create validation scripts for major features
- **MANDATORY**: Include performance metrics in PRs
- **CRITICAL LINEAR ERROR HANDLING**: NEVER proceed if Linear ticket access fails
  - If `mcp__linear__get_issue` fails for any reason, STOP immediately
  - Inform user of the specific error and request manual ticket details
  - Do not guess or assume ticket content
  - Do not proceed with partial information
- **Always check existing code** before implementing new functionality
- **Use the Linear MCP server** to get full context on related tickets
- **Consider the broader system architecture** when making implementation decisions
- **Prioritize privacy and security** in all implementations
- **Document decisions and trade-offs** for future reference

**Implementation is only complete when:**
- ✅ All tests pass (unit, integration, performance)
- ✅ Validation script created and executed successfully
- ✅ PR created using GitHub MCP with comprehensive documentation
- ✅ Performance metrics documented and success criteria met
- ✅ No failed tests

When in doubt, ask clarifying questions about requirements, architecture decisions, or integration approaches. The goal is to build a robust, scalable, and maintainable system that respects user privacy while providing intelligent communication assistance.