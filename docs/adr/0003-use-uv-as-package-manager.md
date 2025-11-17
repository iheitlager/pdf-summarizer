# ADR-0003: Use uv as Package Manager

**Status**: Accepted

**Date**: 2025-11-16

**Technical Story**: Development environment setup and dependency management

## Context

The PDF Summarizer project requires a Python package manager to handle dependency installation, virtual environment management, and project builds. The choice of package manager significantly impacts developer experience, CI/CD performance, and reproducibility.

Key requirements:
- Fast dependency resolution and installation
- Reliable virtual environment creation
- Lock file support for reproducible builds
- Compatible with modern Python packaging standards (PEP 517, PEP 621)
- Good performance for local development and CI/CD
- Support for editable installs and dev dependencies

## Decision

Use **uv** as the primary package manager for the PDF Summarizer project.

uv provides:
- Extremely fast dependency resolution (10-100x faster than pip)
- Built-in virtual environment management (`uv venv`)
- Modern Python packaging standard support (pyproject.toml)
- Lock file generation for reproducibility
- Drop-in replacement for pip commands
- Written in Rust for performance
- Active development and growing ecosystem

### Usage Pattern
```bash
# Virtual environment creation
uv venv .venv --python 3.13

# Install dependencies
uv pip install -e .
uv pip install -e ".[dev]"

# Run commands in virtual environment
uv run pytest
uv run python -m pdf_summarizer.main
uv run ruff check .
```

## Alternatives Considered

### Alternative 1: pip + venv
- **Description**: Standard library tools (pip for packages, venv for environments)
- **Pros**:
  - Built into Python standard library
  - Universally supported
  - Well-documented
  - Most developers familiar with it
- **Cons**:
  - Slow dependency resolution (minutes for complex dependencies)
  - No lock file generation by default
  - Manual virtual environment management
  - Poor performance in CI/CD
  - Limited caching capabilities
- **Rejected because**: Slow performance impacts developer experience and CI/CD times. Modern projects benefit from faster tools with built-in lock file support.

### Alternative 2: Poetry
- **Description**: Modern Python dependency management and packaging tool
- **Pros**:
  - Automatic lock file generation (poetry.lock)
  - Integrated build system
  - Dependency groups for dev/test/docs
  - Good dependency resolution
  - Mature ecosystem
- **Cons**:
  - Slower than uv (still faster than pip)
  - More opinionated about project structure
  - Additional configuration required
  - Uses custom dependency resolver (not pip-compatible)
  - Larger installation footprint
- **Rejected because**: While Poetry is excellent, uv provides similar features with significantly better performance. Poetry's opinionated structure adds complexity without enough benefit for this project.

### Alternative 3: pipenv
- **Description**: Official Python packaging tool with Pipfile/Pipfile.lock
- **Pros**:
  - Lock file support (Pipfile.lock)
  - Automatic virtual environment management
  - Security vulnerability scanning
  - Endorsed by Python Packaging Authority
- **Cons**:
  - Slower dependency resolution than uv
  - Less active development than Poetry or uv
  - Pipfile format less standard than pyproject.toml
  - Performance issues with large dependency trees
  - Virtual environment location sometimes confusing
- **Rejected because**: pipenv has performance issues and uses non-standard Pipfile format. pyproject.toml (PEP 621) is the modern standard, and uv supports it natively.

### Alternative 4: conda/mamba
- **Description**: Cross-language package manager (not Python-specific)
- **Pros**:
  - Handles non-Python dependencies (system libraries)
  - Good for data science projects
  - Binary package distribution
  - Environment management included
- **Cons**:
  - Overkill for pure-Python projects
  - Larger installation size
  - Slower than modern Python-specific tools
  - Conda environments can conflict with pip
  - Not needed for PDF Summarizer dependencies
- **Rejected because**: PDF Summarizer has pure-Python dependencies (Flask, SQLAlchemy, Anthropic). Conda adds unnecessary complexity and slower performance without benefits.

## Consequences

### Positive Consequences
- **10-100x faster installs**: Dependency installation completes in seconds instead of minutes
- **Better CI/CD performance**: Faster test runs and deployments
- **Drop-in pip replacement**: Existing workflows work with minimal changes (`pip install` → `uv pip install`)
- **Modern standards**: Native pyproject.toml support (PEP 621)
- **Developer experience**: Fast iteration with `uv run` commands
- **Reproducible builds**: Lock file support ensures consistent environments
- **Active development**: uv is actively maintained and improving

### Negative Consequences
- **Less mature**: uv is newer than pip/Poetry (but stable for production use)
- **Additional dependency**: Developers must install uv separately
- **Learning curve**: Team must learn `uv run` pattern instead of direct commands
- **Ecosystem adoption**: Some tools may not have uv-specific documentation
- **Compatibility concerns**: Rare edge cases where pip-specific behavior differs

### Neutral Consequences
- **Still pip-compatible**: Uses pip underneath for package installation
- **Virtual environment management**: Requires `uv venv` instead of `python -m venv`
- **Documentation updates**: README and CLAUDE.md emphasize uv usage

## Implementation Notes

### Installation
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Via pip (fallback)
pip install uv
```

### Project Setup
```bash
# Create virtual environment
uv venv .venv --python 3.13

# Install project and dev dependencies
uv pip install -e .
uv pip install -e ".[dev]"
```

### Makefile Integration
All Makefile commands use `uv run` prefix:
```makefile
test:
    uv run pytest

run:
    uv run python -m pdf_summarizer.main

lint:
    uv run ruff check .
```

### Code Locations
- Makefile: [Makefile](../../Makefile)
- Project configuration: [pyproject.toml](../../pyproject.toml)
- Development guide: [CLAUDE.md](../../CLAUDE.md)

### Configuration
```toml
# pyproject.toml
[project]
name = "pdf-summarizer"
requires-python = ">=3.13"
dependencies = [...]

[project.optional-dependencies]
dev = [...]
```

## References

- [uv Documentation](https://github.com/astral-sh/uv)
- [PEP 621 - Storing project metadata in pyproject.toml](https://peps.python.org/pep-0621/)
- [PEP 517 - Backend build system](https://peps.python.org/pep-0517/)
- [Python Packaging User Guide](https://packaging.python.org/)

## Related ADRs

- Related to: ADR-0013 (Use Ruff and Black for Code Quality)
