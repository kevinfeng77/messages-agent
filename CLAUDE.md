# Message Agent Project - Claude Instructions

## Project Overview
This is the Message Agent system - an AI-powered communication assistant that analyzes message patterns, builds user profiles, and provides intelligent response suggestions. The system uses Graphiti for knowledge graph management and spans 4 main phases:

1. **Phase 1**: Data Preparation & Graphiti Integration
2. **Phase 2**: Data Ingestion Pipeline  
3. **Phase 3**: Intelligence Layer
4. **Phase 4**: Live Response System

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

1. **Fetch Ticket Details**
   - Use `mcp__linear__get_issue` to retrieve full ticket information
   - Extract: title, description, estimate, priority, project context

2. **Analyze Technical Context**
   - Identify which phase/component this task belongs to
   - Review related database schemas and existing codebase
   - Consider dependencies and integration points

3. **Generate Implementation Plan**
   - Break down into 3-7 concrete steps
   - Include technical approach and architecture decisions
   - Specify files to create/modify
   - Identify testing requirements
   - Note any dependencies or blockers

4. **Present Plan Structure**
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

5. **Create Feature Branch**
   - ALWAYS create a new branch for each Linear ticket
   - Use naming convention: `kevin/{ticket-description}`
   - Branch from main/master before starting implementation
   - Example: `git checkout -b kevin/refactor-directory-tree`

6. **Await Confirmation**
   - Present plan for review
   - Allow for modifications and refinement
   - Proceed with implementation once approved

7. **Implementation Completion**
   - Always create comprehensive test suite
   - Run validation scripts
   - Create PR automatically using GitHub MCP
   - Include performance metrics and validation results
```

## Project Context & Architecture

### Technology Stack
- **Backend**: Python/TypeScript (TBD based on task)
- **Database**: Neo4j (graph), Redis (queuing), SQLite (current messages)
- **AI/ML**: Graphiti for knowledge graphs, OpenAI/Claude for response generation
- **Infrastructure**: Docker, monitoring with Prometheus/Grafana

### Current Codebase Structure
```
ai_text_agent/
├── src/
│   ├── database/
│   │   ├── manager.py           # SQLite message database management
│   │   ├── migrator.py          # Database migration utilities
│   │   ├── message_migration.py # Message text decoding migration
│   │   └── tests/               # Database-related tests
│   ├── messaging/
│   │   ├── decoder.py           # Message text decoding from binary
│   │   └── tests/               # Messaging-related tests
│   ├── graphiti/
│   │   ├── episode_manager.py   # Graphiti knowledge graph management
│   │   ├── example_script.py    # Graphiti usage examples
│   │   ├── query_manager.py     # Graph query utilities
│   │   └── tests/               # Graphiti-related tests
│   └── utils/
│       ├── logger_config.py     # Logging configuration
│       └── tests/               # Utility tests
├── scripts/                     # Standalone utility scripts
│   ├── migrate_database.py      # Database migration runner
│   ├── validate_implementation.py # Implementation validation
│   └── run_full_migration.py    # Full migration automation
├── data/                        # Message databases and exports
├── logs/                        # Application logs
├── tests/                       # Integration tests
└── requirements.txt             # Python dependencies
```

### Key Design Principles
- **Privacy First**: Encryption, PII protection, user consent
- **Minimal Viable Entities**: Start simple, let Graphiti build complexity
- **Real-time Processing**: Streaming ingestion with queue management
- **Extensible Architecture**: Support multiple messaging platforms
- **Observable Systems**: Comprehensive logging, metrics, and monitoring

## Common Patterns & Guidelines

### For Database Tasks
- Use existing `database_manager.py` patterns
- Implement proper error handling and logging
- Include migration scripts for schema changes
- Write comprehensive tests for data operations

### For API Development
- Follow RESTful conventions
- Implement proper authentication and rate limiting
- Include OpenAPI/Swagger documentation
- Use structured logging with correlation IDs

### For Graphiti Integration
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
- Minimum 80% code coverage for new code
- All tests must pass before PR creation
- Include both positive and negative test cases
- Test with real data samples when available
- Document test approach in implementation plan

**Test File Structure:**
```
tests/
├── unit/
│   └── test_[module_name].py
├── integration/
│   └── test_[feature_name]_integration.py
└── validation/
    └── validate_[feature_name].py
```

## Git Workflow & Branch Management

### Branch Naming Convention
All branches should follow the pattern: `kevin/{description-of-changes-in-few-words}`

**Examples:**
- `kevin/person-entity-schema`
- `kevin/neo4j-setup`
- `kevin/message-validation`
- `kevin/response-generation-api`

### Pull Request Guidelines

**PR Title Format:** `[LINEAR-TICKET-NUMBER] Quick description`

**Examples:**
- `[SERENE-11] Create Person entity schema definition`
- `[SERENE-27] Set up Neo4j development environment`
- `[SERENE-35] Design batch processing chunking strategy`

**PR Process:**
1. **Create Feature Branch**
   ```bash
   git checkout -b kevin/{short-description}
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
# Install dependencies
pip install -r requirements.txt

# Run database migrations
python src/database_migrator.py

# Run tests (when test suite is implemented)
pytest tests/

# Start development server (when API is implemented)
python -m uvicorn main:app --reload
```

### Git Commands
```bash
# Create and switch to feature branch
git checkout -b kevin/{description}

# Add and commit changes
git add .
git commit -m "Implement [feature description]"

# Push branch (PR creation handled by MCP)
git push -u origin kevin/{description}

# After PR approval, clean up
git checkout main
git pull origin main
git branch -d kevin/{description}
```

### GitHub MCP Workflow (PREFERRED METHOD)
**ALWAYS use GitHub MCP tools instead of external CLI tools:**

```python
# Create Pull Request
mcp__github__create_pull_request(
    owner="kevinfeng77",
    repo="messages-agent", 
    title="[LINEAR-TICKET] Description",
    head="kevin/{branch-name}",
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

### Linting & Quality (MANDATORY BEFORE PR)
```bash
# Format code (REQUIRED)
black src/
isort src/

# Type checking (REQUIRED)
mypy src/

# Linting (REQUIRED)
flake8 src/

# Verify all checks pass locally before pushing
black --check src/ && isort --check-only src/ && flake8 src/ && mypy src/
```

**MANDATORY Pre-Push Checks:**
- All linting tools must pass before pushing changes
- Use the verification command above to ensure GitHub Actions will pass
- Never push code that fails local linting checks

## Linear Project Mapping

- **Phase 1 Tasks**: Data schema design, conversation detection, Graphiti setup
- **Phase 2 Tasks**: Message transformation, real-time ingestion, data quality
- **Phase 3 Tasks**: User profiling, contextual search, response generation
- **Phase 4 Tasks**: Message interception, live responses, monitoring

## Complete Implementation Workflow

### MANDATORY Implementation Steps (Always Follow):

1. **Plan Generation**
   - Fetch Linear ticket details using MCP
   - Generate detailed implementation plan
   - Include testing strategy and success criteria

2. **Branch Creation (MANDATORY)**
   - **ALWAYS create a new feature branch** for each Linear ticket
   - Use naming convention: `kevin/{ticket-description}` (e.g., `kevin/refactor-directory-tree`)
   - Create branch from main/master: `git checkout -b kevin/{description}`
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

6. **PR Creation (Use GitHub MCP)**
   - Commit all changes with descriptive messages
   - Push branch to origin
   - Use `mcp__github__create_pull_request` to create PR
   - Include comprehensive description with:
     - Problem statement and solution
     - Performance metrics and validation results  
     - Testing checklist (all items checked)
     - Impact and value delivered

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

## Notes for Claude

- **MANDATORY**: Always create comprehensive test suites
- **MANDATORY**: Use GitHub MCP for all GitHub operations
- **MANDATORY**: Create validation scripts for major features
- **MANDATORY**: Include performance metrics in PRs
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
- ✅ Code coverage ≥80% for new functionality

When in doubt, ask clarifying questions about requirements, architecture decisions, or integration approaches. The goal is to build a robust, scalable, and maintainable system that respects user privacy while providing intelligent communication assistance.