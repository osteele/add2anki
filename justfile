# Justfile for add2anki project

# Default recipe to run when just is called without arguments
default:
    @just --list

# Install dependencies
setup:
    uv sync --frozen

# Clean up build artifacts
clean:
    rm -rf dist

# Format code with ruff
format:
    uv run --dev ruff format .
    uv run --dev ruff check --fix-only .

# Like format, but also shows unfixable issues that need manual attention
fix:
    uv run --dev ruff format .
    uv run --dev ruff check --fix --unsafe-fixes .

# Publish to PyPI
publish: clean
    uv build
    uv publish

# Verify code quality without modifying files
lint:
    uv run --dev ruff check .
    uv run --dev pyright

# Run type checking with pyright
typecheck:
    uv run --dev pyright add2anki

# Run tests with pytest
test *ARGS:
    uv run --dev pytest {{ARGS}}

# Run all checks: linting, type checking, and tests
check: lint typecheck test
    @echo "All checks passed!"

# Run the application
run *ARGS:
    uv run python -m add2anki.cli {{ARGS}}
