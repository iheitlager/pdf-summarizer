# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records for the PDF Summarizer project.

## What are ADRs?

Architecture Decision Records document significant architectural and design decisions made in this project, including:
- The context and problem being addressed
- The decision made
- Consequences and trade-offs
- Alternatives considered

## Format

We use the [Markdown Any Decision Records (MADR)](https://adr.github.io/madr/) format with these sections:
- **Status**: Proposed | Accepted | Deprecated | Superseded
- **Context**: What is the issue we're seeing that motivates this decision?
- **Decision**: What is the change we're proposing and/or doing?
- **Consequences**: What becomes easier or more difficult as a result?

## Current ADRs

### Recommended ADRs (Based on Current Architecture)

Based on analysis of the codebase, these are the significant architectural decisions that should be documented:

#### **Foundation & Technology Stack**
1. **ADR-0001: Use Flask as Web Framework** ✅ Created
2. **ADR-0002: Use SQLite with SQLAlchemy ORM** ✅ Created
3. **ADR-0003: Use uv as Package Manager** ✅ Created
4. **ADR-0004: Use Anthropic Claude API for Summarization** ✅ Created

#### **Architecture & Design Patterns**
5. **ADR-0005: Monolithic Application Architecture** ✅ Created
6. **ADR-0006: SHA256 Hash-Based Caching Mechanism** ✅ Created
7. **ADR-0007: Session-Based User Tracking Without Authentication** ✅ Created
8. **ADR-0008: Store PDF Files on Filesystem, Not Database** ✅ Created

#### **Infrastructure & Operations**
9. **ADR-0009: Use APScheduler for Background Cleanup Jobs** ✅ Created
10. **ADR-0010: Use Flask-Limiter for Rate Limiting** ✅ Created
11. **ADR-0011: Multi-File Logging Strategy** ✅ Created

#### **Testing & Quality**
12. **ADR-0012: In-Memory SQLite for Testing** ✅ Created
13. **ADR-0013: Use Ruff and Black for Code Quality** ✅ Created

## Index of ADRs

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](0001-use-flask-as-web-framework.md) | Use Flask as Web Framework | Accepted | 2025-11-16 |
| [0002](0002-use-sqlite-with-sqlalchemy-orm.md) | Use SQLite with SQLAlchemy ORM | Accepted | 2025-11-16 |
| [0003](0003-use-uv-as-package-manager.md) | Use uv as Package Manager | Accepted | 2025-11-16 |
| [0004](0004-use-anthropic-claude-api.md) | Use Anthropic Claude API for Summarization | Accepted | 2025-11-16 |
| [0005](0005-monolithic-application-architecture.md) | Monolithic Application Architecture | Accepted | 2025-11-16 |
| [0006](0006-sha256-hash-based-caching.md) | SHA256 Hash-Based Caching Mechanism | Accepted | 2025-11-16 |
| [0007](0007-session-based-user-tracking.md) | Session-Based User Tracking Without Authentication | Accepted | 2025-11-16 |
| [0008](0008-store-files-on-filesystem.md) | Store PDF Files on Filesystem, Not Database | Accepted | 2025-11-16 |
| [0009](0009-use-apscheduler-for-background-jobs.md) | Use APScheduler for Background Cleanup Jobs | Accepted | 2025-11-16 |
| [0010](0010-use-flask-limiter-for-rate-limiting.md) | Use Flask-Limiter for Rate Limiting | Accepted | 2025-11-16 |
| [0011](0011-multi-file-logging-strategy.md) | Multi-File Logging Strategy | Accepted | 2025-11-16 |
| [0012](0012-in-memory-sqlite-for-testing.md) | In-Memory SQLite for Testing | Accepted | 2025-11-16 |
| [0013](0013-use-ruff-and-black.md) | Use Ruff and Black for Code Quality | Accepted | 2025-11-16 |

## Creating New ADRs

When making a significant architectural decision:

1. **Create a new ADR file**: `XXXX-short-title.md`
2. **Use the template**: Copy from [template.md](template.md)
3. **Number sequentially**: Start from 0014
4. **Update this README**: Add to the index table
5. **Update CHANGELOG.md**: Document the ADR creation

## ADR Lifecycle

- **Proposed**: Decision is being discussed
- **Accepted**: Decision has been made and implemented
- **Deprecated**: Decision is still in effect but should not be used for new work
- **Superseded**: Decision has been replaced (link to new ADR)

## Related Documentation

- [Database Schema](../database.md) - Technical database documentation
- [CLAUDE.md](../../CLAUDE.md) - Developer guidelines
- [README.md](../../README.md) - User documentation

---

**Last Updated**: 2025-11-16
**Total ADRs**: 13
