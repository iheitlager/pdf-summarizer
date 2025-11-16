# Documentation

This directory contains detailed technical documentation for the PDF Summarizer application.

## Available Documentation

### [Database Schema](./database.md)
Complete database schema reference including:
- Table definitions (Upload, Summary)
- Column specifications and data types
- Relationships and foreign keys
- Indexes and constraints
- Caching mechanism details
- Common query patterns
- Migration guide
- Performance considerations
- Backup and recovery procedures

### [Architecture Decision Records (ADRs)](./adr/)
Documents significant architectural and design decisions:
- Technology choices (Flask, SQLite, uv, Claude API)
- Design patterns (monolithic architecture, caching, sessions)
- Infrastructure decisions (APScheduler, rate limiting, logging)
- Testing and quality strategies
- **[ADR Recommendations](./ADR_RECOMMENDATIONS.md)** - Full analysis of current architecture with validation results
- **[ADR Index](./adr/README.md)** - List of all ADRs with status and dates

## Quick Links

- **User Guide**: See main [README.md](../README.md)
- **Developer Guide**: See [CLAUDE.md](../CLAUDE.md)
- **Version History**: See [CHANGELOG.md](../CHANGELOG.md)
- **Database Models**: [src/pdf_summarizer/main.py](../src/pdf_summarizer/main.py#L91-L121)

## Contributing to Documentation

When updating documentation:

1. Keep technical details in `docs/`
2. Keep user-facing info in main `README.md`
3. Keep development workflow in `CLAUDE.md`
4. Update version in all three locations when releasing

---

**Last Updated**: 2025-11-16
