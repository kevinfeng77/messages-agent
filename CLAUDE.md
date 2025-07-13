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

5. **Await Confirmation**
   - Present plan for review
   - Allow for modifications and refinement
   - Proceed with implementation once approved
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
│   ├── database_manager.py     # SQLite message database management
│   ├── database_migrator.py    # Database migration utilities
│   └── logger_config.py        # Logging configuration
├── data/                       # Message databases and exports
├── logs/                       # Application logs
└── requirements.txt            # Python dependencies
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

### For Testing
- Unit tests for business logic
- Integration tests for database operations
- End-to-end tests for critical user flows
- Performance tests for high-throughput scenarios

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

3. **Create Pull Request**
   - Use proper title format with Linear ticket number
   - Include implementation summary in PR description
   - Link to the Linear ticket
   - Request code review

4. **PR Template**
   ```markdown
   ## Summary
   [Brief description of changes]

   ## Linear Ticket
   Closes [Linear ticket URL]

   ## Implementation Details
   - [Key implementation points]
   - [Architecture decisions made]
   - [Testing approach]

   ## Testing
   - [ ] Unit tests added/updated
   - [ ] Integration tests passing
   - [ ] Manual testing completed

   ## Checklist
   - [ ] Code follows project conventions
   - [ ] Documentation updated
   - [ ] No breaking changes (or properly documented)
   - [ ] Logging and error handling included
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

# Push branch and create PR
git push -u origin kevin/{description}

# After PR approval, clean up
git checkout main
git pull origin main
git branch -d kevin/{description}
```

### Linting & Quality
```bash
# Format code
black src/
isort src/

# Type checking
mypy src/

# Linting
flake8 src/
```

## Linear Project Mapping

- **Phase 1 Tasks**: Data schema design, conversation detection, Graphiti setup
- **Phase 2 Tasks**: Message transformation, real-time ingestion, data quality
- **Phase 3 Tasks**: User profiling, contextual search, response generation
- **Phase 4 Tasks**: Message interception, live responses, monitoring

## Notes for Claude

- **Always check existing code** before implementing new functionality
- **Use the Linear MCP server** to get full context on related tickets
- **Consider the broader system architecture** when making implementation decisions
- **Prioritize privacy and security** in all implementations
- **Include proper error handling and logging** in all code
- **Write tests alongside implementation** for reliability
- **Document decisions and trade-offs** for future reference

When in doubt, ask clarifying questions about requirements, architecture decisions, or integration approaches. The goal is to build a robust, scalable, and maintainable system that respects user privacy while providing intelligent communication assistance.