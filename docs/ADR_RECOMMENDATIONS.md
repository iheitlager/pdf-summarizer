# Architecture Decision Records - Recommendations

**Date**: 2025-11-16
**Project**: PDF Summarizer v0.2.4

## Project Validation Results

### ✅ Code Quality
```
Tests:        134/134 passed (95% coverage)
Linting:      All checks passed (Ruff)
Type Checks:  Success (MyPy)
```

### 📊 Code Coverage by Module
- `src/pdf_summarizer/__init__.py`: 100%
- `src/pdf_summarizer/config.py`: 98%
- `src/pdf_summarizer/logging_config.py`: 98%
- `src/pdf_summarizer/utils.py`: 97%
- `src/pdf_summarizer/main.py`: 93%
- **Overall**: 95%

## Identified Architectural Decisions

After analyzing the codebase, I've identified **13 significant architectural decisions** that should be documented as ADRs. These decisions fall into four categories:

### 1. Foundation & Technology Stack (4 ADRs)

These decisions establish the core technology choices for the application:

#### **ADR-0001: Use Flask as Web Framework** ✅ CREATED
- **Status**: Accepted
- **Summary**: Chose Flask over Django, FastAPI, and Bottle for its simplicity and extension ecosystem
- **Impact**: Enables rapid development with minimal boilerplate
- **Location**: [docs/adr/0001-use-flask-as-web-framework.md](adr/0001-use-flask-as-web-framework.md)

#### **ADR-0002: Use SQLite with SQLAlchemy ORM** ✅ CREATED
- **Status**: Accepted
- **Summary**: Chose SQLite over PostgreSQL/MySQL for simplicity, zero configuration, and portability
- **Impact**: Single-file database, no server required, perfect for educational/demo use
- **Location**: [docs/adr/0002-use-sqlite-with-sqlalchemy-orm.md](adr/0002-use-sqlite-with-sqlalchemy-orm.md)

#### **ADR-0003: Use uv as Package Manager** ⏳ RECOMMENDED
- **Status**: Proposed
- **Summary**: Chose uv over pip/poetry for faster installs and better dependency resolution
- **Impact**: Faster development workflow, explicit in project structure
- **Key Points to Document**:
  - Why uv over pip, poetry, pipenv
  - Benefits: Speed, reliability, deterministic installs
  - Trade-offs: Newer tool, smaller ecosystem
  - Makefile integration for consistent usage

#### **ADR-0004: Use Anthropic Claude API for Summarization** ⏳ RECOMMENDED
- **Status**: Proposed
- **Summary**: Chose Claude over OpenAI GPT, local models (LLaMA), or extractive summarization
- **Impact**: High-quality summaries with simple API integration
- **Key Points to Document**:
  - Why Claude over alternatives (quality, API simplicity, pricing)
  - Model choice (claude-sonnet-4-5-20250929)
  - Trade-offs: API costs, external dependency, latency
  - Cost optimization via caching (ADR-0006)

### 2. Architecture & Design Patterns (4 ADRs)

These decisions define how the application is structured and operates:

#### **ADR-0005: Monolithic Application Architecture** ⏳ RECOMMENDED
- **Status**: Proposed
- **Summary**: Single Flask application vs. microservices or modular architecture
- **Impact**: Simplicity at the cost of scalability
- **Key Points to Document**:
  - Why monolith over microservices
  - Single main.py with all routes, models, helpers
  - Benefits: Simple deployment, no service coordination
  - Trade-offs: All-or-nothing scaling, tight coupling
  - Future path: Could extract summarization service if needed

#### **ADR-0006: SHA256 Hash-Based Caching Mechanism** ✅ CREATED
- **Status**: Accepted
- **Summary**: Content-based deduplication using SHA256 hashing for 60% cost reduction
- **Impact**: Major cost optimization, unique feature of the application
- **Location**: [docs/adr/0006-sha256-hash-based-caching.md](adr/0006-sha256-hash-based-caching.md)

#### **ADR-0007: Session-Based User Tracking Without Authentication** ✅ CREATED
- **Status**: Accepted
- **Summary**: UUID sessions instead of user accounts for frictionless experience
- **Impact**: Privacy-friendly, no registration required, enables personalization
- **Location**: [docs/adr/0007-session-based-user-tracking.md](adr/0007-session-based-user-tracking.md)

#### **ADR-0008: Store PDF Files on Filesystem, Not Database** ⏳ RECOMMENDED
- **Status**: Proposed
- **Summary**: Store binary PDFs in uploads/ folder, only metadata in database
- **Impact**: Better performance, easier backup, standard practice
- **Key Points to Document**:
  - Why filesystem over BLOB storage in database
  - Benefits: Performance, standard tools (rsync, tar), size limits
  - Trade-offs: Two-phase backup (DB + files), file cleanup required
  - Implementation: Cascade delete DB, manual file deletion
  - Code location: utils.py save_uploaded_file()

### 3. Infrastructure & Operations (3 ADRs)

These decisions cover how the application handles ongoing operations:

#### **ADR-0009: Use APScheduler for Background Cleanup Jobs** ⏳ RECOMMENDED
- **Status**: Proposed
- **Summary**: APScheduler for daily cleanup vs. cron, Celery, or manual cleanup
- **Impact**: Automated maintenance without external dependencies
- **Key Points to Document**:
  - Why APScheduler over cron (cross-platform), Celery (overkill)
  - Daily cleanup job at 3 AM (configurable)
  - In-process scheduler vs. separate worker
  - Trade-offs: Single-server only, no distributed jobs
  - Code location: main.py cleanup_old_uploads()

#### **ADR-0010: Use Flask-Limiter for Rate Limiting** ⏳ RECOMMENDED
- **Status**: Proposed
- **Summary**: Flask-Limiter with memory backend for abuse prevention
- **Impact**: Prevents API quota exhaustion and DoS attacks
- **Key Points to Document**:
  - Why Flask-Limiter over custom middleware
  - Limits: 10 uploads/hour, 200 requests/day
  - Memory backend (could upgrade to Redis)
  - Key function: get_remote_address (IP-based)
  - Trade-offs: Memory backend doesn't persist across restarts
  - Code location: main.py limiter initialization

#### **ADR-0011: Multi-File Logging Strategy** ⏳ RECOMMENDED
- **Status**: Proposed
- **Summary**: Separate log files (app.log, error.log, api.log) with rotation
- **Impact**: Better debugging and monitoring
- **Key Points to Document**:
  - Why separate logs vs. single log file
  - app.log: General INFO+ messages
  - error.log: ERROR+ only for alerts
  - api.log: External Claude API calls (audit trail)
  - Rotating file handlers (10MB, 5 backups)
  - LOG_LEVEL environment variable
  - Code location: logging_config.py

### 4. Testing & Quality (2 ADRs)

These decisions ensure code quality and reliability:

#### **ADR-0012: In-Memory SQLite for Testing** ⏳ RECOMMENDED
- **Status**: Proposed
- **Summary**: Use `sqlite:///:memory:` for fast isolated tests
- **Impact**: Fast test execution, no test pollution
- **Key Points to Document**:
  - Why in-memory vs. file-based test DB
  - Benefits: Speed (~1.5s for 134 tests), isolation, no cleanup
  - Trade-offs: Can't inspect DB after tests, SQLite-specific
  - Fixtures: conftest.py creates fresh DB per test
  - Mock Anthropic API to avoid real API calls
  - 95% code coverage target
  - Code location: tests/conftest.py

#### **ADR-0013: Use Ruff and Black for Code Quality** ⏳ RECOMMENDED
- **Status**: Proposed
- **Summary**: Ruff for linting, Black for formatting (100-char line length)
- **Impact**: Consistent code style, catch bugs early
- **Key Points to Document**:
  - Why Ruff over Pylint/Flake8 (speed, modern)
  - Why Black (opinionated, no bikeshedding)
  - 100-char line length (vs. 88 default)
  - MyPy for type checking (permissive config)
  - Makefile targets: make lint, make format, make type-check
  - Pre-commit integration (optional)
  - Configuration: pyproject.toml

## ADR Summary Matrix

| # | Title | Category | Status | Priority | Created |
|---|-------|----------|--------|----------|---------|
| 0001 | Flask Framework | Foundation | ✅ Accepted | High | Yes |
| 0002 | SQLite + SQLAlchemy | Foundation | ✅ Accepted | High | Yes |
| 0003 | uv Package Manager | Foundation | ⏳ Proposed | Medium | No |
| 0004 | Anthropic Claude API | Foundation | ⏳ Proposed | High | No |
| 0005 | Monolithic Architecture | Design | ⏳ Proposed | Medium | No |
| 0006 | SHA256 Caching | Design | ✅ Accepted | High | Yes |
| 0007 | Session Tracking | Design | ✅ Accepted | High | Yes |
| 0008 | Filesystem Storage | Design | ⏳ Proposed | Medium | No |
| 0009 | APScheduler | Operations | ⏳ Proposed | Low | No |
| 0010 | Flask-Limiter | Operations | ⏳ Proposed | Medium | No |
| 0011 | Multi-File Logging | Operations | ⏳ Proposed | Low | No |
| 0012 | In-Memory Testing | Testing | ⏳ Proposed | Medium | No |
| 0013 | Ruff + Black | Testing | ⏳ Proposed | Low | No |

## Recommendation: Next Steps

### Immediate Actions (High Priority)
1. ✅ **Validate ADR structure** - Template and README created
2. ✅ **Create foundational ADRs** - Flask, SQLite, SHA256 Caching, Session Tracking
3. ⏳ **Create ADR-0004** - Document Claude API choice and model selection
4. ⏳ **Create ADR-0003** - Document uv package manager rationale

### Medium Priority (Next Sprint)
5. Create ADR-0005 (Monolithic Architecture) - Important for future scaling decisions
6. Create ADR-0008 (Filesystem Storage) - Standard but worth documenting
7. Create ADR-0010 (Flask-Limiter) - Security-relevant decision
8. Create ADR-0012 (In-Memory Testing) - Helps onboard contributors

### Lower Priority (As Needed)
9. Create ADR-0009 (APScheduler) - Straightforward choice
10. Create ADR-0011 (Multi-File Logging) - Operational detail
11. Create ADR-0013 (Ruff + Black) - Tooling choice

### Update Documentation
- ✅ Add `docs/adr/` to project structure in README.md
- ✅ Reference ADRs from CLAUDE.md
- ⏳ Link ADRs from relevant code comments (e.g., "See ADR-0006 for caching rationale")
- ⏳ Mention ADRs in CHANGELOG when architectural changes occur

## ADR Template

Use the template at [docs/adr/template.md](adr/template.md) for creating new ADRs. Each ADR should include:
- Context and problem statement
- Decision made
- Alternatives considered (with pros/cons)
- Consequences (positive, negative, neutral)
- Implementation notes with code locations
- References and related ADRs

## Benefits of ADRs

By documenting these decisions, the project gains:

1. **Knowledge Transfer**: New contributors understand *why* choices were made
2. **Historical Context**: Future maintainers see reasoning, not just results
3. **Decision Audit Trail**: Track evolution of architecture over time
4. **Avoid Rehashing**: Don't revisit settled decisions without new information
5. **Transparency**: Users and stakeholders see thought process
6. **Learning Resource**: Serves as educational material for architectural patterns

## Related Documentation

- **ADR Directory**: [docs/adr/](adr/)
- **Database Schema**: [docs/database.md](database.md)
- **Developer Guide**: [CLAUDE.md](../CLAUDE.md)
- **Version History**: [CHANGELOG.md](../CHANGELOG.md)

---

**Created**: 2025-11-16
**Author**: PDF Summarizer Development Team
**Version**: 1.0
