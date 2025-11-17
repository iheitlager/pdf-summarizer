# ADR-0013: Use Ruff and Black for Code Quality

**Status**: Accepted

**Date**: 2025-11-16

**Technical Story**: Code formatting and linting standards

## Context

The PDF Summarizer requires consistent code style and quality checking to maintain readability and catch potential bugs. The project needs tools for:

- **Code formatting**: Consistent style across all files (spacing, line length, imports)
- **Linting**: Detect common errors, anti-patterns, and code smells
- **Import sorting**: Organize imports consistently
- **Type checking**: Optional static type analysis
- **Fast execution**: Quick feedback during development
- **CI/CD integration**: Automated checks in pull requests

Key requirements:
- Fast execution (< 1 second for full codebase)
- Automatic fixing where possible
- Minimal configuration required
- Compatible with Python 3.13
- Good developer experience (clear error messages)

## Decision

Use **Ruff** for linting and import sorting, combined with **Black** for code formatting.

### Ruff (Linter + Import Sorter)
- **Extremely fast**: 10-100x faster than Flake8/Pylint
- **Comprehensive**: Replaces Flake8, isort, pyupgrade, and more
- **Auto-fix**: Automatically fixes many issues
- **Written in Rust**: Native performance
- **100+ rules**: Covers common errors, style, best practices

### Black (Code Formatter)
- **Opinionated**: No style arguments (deterministic formatting)
- **Widely adopted**: Industry standard Python formatter
- **Stable**: Minimal configuration changes over time
- **Line length**: 100 characters (configured)

### Configuration
```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP"]
ignore = ["E501"]  # Black handles line length

[tool.black]
line-length = 100
target-version = ['py313']
```

### Makefile Integration
```makefile
lint:
    uv run ruff check .

format:
    uv run black .
    uv run ruff check . --fix
```

## Alternatives Considered

### Alternative 1: Flake8 + isort + pyupgrade
- **Description**: Traditional Python linting stack
- **Pros**:
  - Mature ecosystem
  - Widely adopted
  - Many plugins available
  - Well-documented
  - Familiar to most Python developers
- **Cons**:
  - Much slower than Ruff (10-100x)
  - Requires multiple tools (flake8, isort, pyupgrade)
  - More configuration needed
  - No auto-fix for most issues
  - Slower feedback loop
  - Multiple dependencies to manage
- **Rejected because**: Ruff provides same functionality 10-100x faster in single tool. Development velocity more important than ecosystem maturity.

### Alternative 2: Pylint
- **Description**: Comprehensive Python linter with advanced checks
- **Pros**:
  - Very thorough analysis
  - Detects complex code smells
  - Configurable severity levels
  - Good for large codebases
  - Code quality scores
- **Cons**:
  - Extremely slow (minutes for medium codebase)
  - Overly strict by default (many false positives)
  - Complex configuration required
  - Opinionated about design patterns
  - Poor developer experience (noisy output)
  - Discourages frequent running
- **Rejected because**: Too slow and too opinionated for small project. Ruff provides essential checks with 100x better performance.

### Alternative 3: Autopep8/YAPF (Instead of Black)
- **Description**: Alternative code formatters with more configuration
- **Pros**:
  - More configurable than Black
  - Can tune specific formatting rules
  - Preserve some developer style choices
- **Cons**:
  - Configuration debates (wastes time)
  - Less consistent (different configs = different style)
  - Not as widely adopted as Black
  - More decisions required
  - Team arguments about formatting
- **Rejected because**: Black's opinionated approach prevents bikeshedding. No configuration means no arguments about style. Standard in Python community.

### Alternative 4: Ruff Only (No Black)
- **Description**: Use Ruff's built-in formatter instead of Black
- **Pros**:
  - Single tool for everything
  - Slightly faster (no Black invocation)
  - Consistent tooling
  - Less dependencies
- **Cons**:
  - Ruff formatter newer/less mature
  - Black is industry standard
  - Black has broader adoption
  - Ruff formatter still evolving
  - Some Black features not yet in Ruff
- **Rejected because**: Black is battle-tested and stable. Ruff formatter is improving but Black remains standard. Can revisit when Ruff formatter matures.

### Alternative 5: mypy for Strict Type Checking
- **Description**: Add comprehensive type checking with mypy
- **Pros**:
  - Catches type errors before runtime
  - Better IDE autocomplete
  - Enforces type hints
  - Good for large codebases
  - Industry standard type checker
- **Cons**:
  - Requires type hints everywhere (time-consuming)
  - Steep learning curve
  - Can be overly strict
  - Third-party library stubs needed
  - Not critical for small codebase
- **Rejected for strict enforcement, but available**: mypy installed in dev dependencies for optional use. Not enforced in CI/CD. Type hints encouraged but not required.

## Consequences

### Positive Consequences
- **Extremely fast**: Ruff lints entire codebase in < 1 second
- **Consistent formatting**: Black ensures uniform code style
- **Auto-fix**: Ruff fixes many issues automatically
- **Single command**: `make format` fixes most issues
- **No style debates**: Black's opinions prevent bikeshedding
- **Good developer UX**: Fast feedback encourages frequent use
- **CI/CD ready**: Fast enough to run on every commit
- **Modern Python**: Pyupgrade rules modernize code automatically

### Negative Consequences
- **Opinionated**: Cannot customize Black formatting (by design)
- **Learning curve**: Developers must accept Black's style
- **Breaking changes**: Formatting may change existing code
- **Line length debates**: Some prefer 88 (Black default) vs 100
- **Import reordering**: Ruff may reorder imports unexpectedly

### Neutral Consequences
- **Two tools**: Ruff + Black instead of one (acceptable trade-off)
- **Configuration**: Minimal config in pyproject.toml
- **Pre-commit hooks**: Can integrate with pre-commit framework

## Implementation Notes

### Installation
```toml
# pyproject.toml
[project.optional-dependencies]
dev = [
    "ruff>=0.8.0",
    "black>=24.0.0",
    "mypy>=1.8.0",  # Optional, not enforced
]
```

### Configuration
```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py313']
include = '\.pyi?$'
extend-exclude = '''
/(
  \.eggs | \.git | \.venv | build | dist
)/
'''

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long (Black handles)
    "B008",  # do not perform function calls in argument defaults
    "C901",  # too complex
]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]  # Allow unused imports in __init__
```

### Makefile Commands
```makefile
# Check code style without fixing
lint:
    uv run ruff check .

# Format code and fix auto-fixable issues
format:
    uv run black .
    uv run ruff check . --fix

# Type check (optional)
type-check:
    uv run mypy src/
```

### Code Locations
- Configuration: [pyproject.toml:44-80](../../pyproject.toml#L44-L80)
- Makefile: [Makefile](../../Makefile)

## Ruff Rule Categories

### Enabled Rules
```python
# E/W - pycodestyle (PEP 8 style)
E501  # Line too long (handled by Black)
W503  # Line break before binary operator

# F - Pyflakes (logical errors)
F401  # Unused import
F841  # Unused variable
F811  # Redefinition of unused name

# I - isort (import sorting)
I001  # Import block unsorted

# B - flake8-bugbear (common bugs)
B006  # Mutable default argument
B008  # Function call in argument defaults

# C4 - flake8-comprehensions (better comprehensions)
C400  # Use list comprehension instead of list(generator)

# UP - pyupgrade (modern Python)
UP006  # Use dict() instead of {}
UP032  # Use f-strings instead of .format()
```

## Usage Examples

### Check Code Quality
```bash
# Lint without fixing
$ uv run ruff check .
src/pdf_summarizer/main.py:123:5: F841 Local variable `unused_var` is assigned to but never used
src/pdf_summarizer/utils.py:45:1: I001 Import block is unsorted or unformatted

# Fix auto-fixable issues
$ uv run ruff check . --fix
Fixed 12 errors

# Format with Black
$ uv run black .
reformatted src/pdf_summarizer/main.py
reformatted src/pdf_summarizer/utils.py
```

### Pre-Commit Hook (Optional)
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.0.0
    hooks:
      - id: black
        language_version: python3.13

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
```

## CI/CD Integration

### GitHub Actions Example
```yaml
# .github/workflows/test.yml
- name: Check code quality
  run: |
    uv run ruff check .
    uv run black --check .
```

### Failing Build on Issues
```bash
# Exit with error if unfixed issues
uv run ruff check .
uv run black --check .

# Both commands exit non-zero if issues found
```

## Performance Comparison

### Ruff vs Flake8 + isort
```bash
# Ruff (Rust-based)
$ time uv run ruff check .
real    0m0.142s

# Flake8 + isort (Python-based)
$ time uv run flake8 .
$ time uv run isort --check .
real    0m2.567s
```

**Verdict**: Ruff is ~18x faster for this codebase.

## Migration from Other Tools

### From Flake8
```bash
# Flake8 config → Ruff config
# .flake8
max-line-length = 100
ignore = E501,W503

# pyproject.toml (Ruff equivalent)
[tool.ruff]
line-length = 100
ignore = ["E501", "W503"]
```

### From isort
```bash
# isort config → Ruff config (built-in)
# Ruff handles import sorting with "I" rule category
[tool.ruff.lint]
select = ["I"]
```

## References

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Rules](https://docs.astral.sh/ruff/rules/)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)

## Related ADRs

- Related to: ADR-0003 (Use uv as Package Manager) - Tool execution via uv
- Related to: ADR-0012 (In-Memory SQLite for Testing) - Code quality in tests
