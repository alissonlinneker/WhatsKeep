# Contributing to WhatsKeep

Thank you for your interest in contributing to WhatsKeep! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Getting Started

1. Fork and clone the repository:

```bash
git clone https://github.com/<your-username>/whatskeep.git
cd whatskeep
```

2. Install development dependencies:

```bash
# With uv (recommended)
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
```

3. Verify your setup:

```bash
pytest tests/ -v
ruff check src/ tests/
mypy src/whatskeep/ --ignore-missing-imports
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=whatskeep --cov-report=term-missing

# Run a specific test file
pytest tests/test_detector.py -v
```

## Linting and Type Checking

```bash
# Lint with ruff
ruff check src/ tests/

# Auto-fix lint issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/

# Type check with mypy
mypy src/whatskeep/ --ignore-missing-imports
```

## Code Style

- We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting
- Line length limit: **100 characters**
- Follow existing code patterns and conventions
- Add type hints to all public functions and methods
- Write docstrings for all public modules, classes, and functions

## Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/) in English:

- `feat:` — new feature
- `fix:` — bug fix
- `refactor:` — code refactoring (no behavior change)
- `docs:` — documentation changes
- `test:` — adding or updating tests
- `chore:` — maintenance tasks (CI, dependencies, etc.)

Examples:

```
feat: add support for WhatsApp voice note detection
fix: handle missing database on first run
docs: update installation instructions for Windows
test: add integration tests for file watcher
```

## Pull Request Process

1. Create a feature branch from `main`:

```bash
git checkout -b feat/my-feature main
```

2. Make your changes and ensure all checks pass:

```bash
pytest tests/ -v
ruff check src/ tests/
mypy src/whatskeep/ --ignore-missing-imports
```

3. Commit your changes following the commit conventions above.

4. Push your branch and open a Pull Request against `main`.

5. Fill out the PR template with a clear description of your changes.

6. Wait for CI to pass and a maintainer to review your PR.

## Issue Templates

When reporting bugs or requesting features, please use the provided issue templates:

- **Bug Report** — for reporting unexpected behavior
- **Feature Request** — for suggesting new functionality

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful, inclusive, and constructive in all interactions.

## Questions?

If you have questions about contributing, feel free to open a discussion or reach out by creating an issue.
