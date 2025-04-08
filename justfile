# Justfile for add2anki project

# Default recipe to run when just is called without arguments
default:
    @just --list

# Install dependencies
setup:
    uv sync --frozen

# Run all checks: linting, type checking, and tests
check: lint typecheck test
    @echo "All checks passed!"

# Clean up build artifacts
clean:
    rm -rf dist

# Like format, but also shows unfixable issues that need manual attention
fix:
    uv run --dev ruff format add2anki tests
    uv run --dev ruff check --fix --unsafe-fixes .

# Format code with ruff
format:
    uv run --dev ruff format add2anki tests
    uv run --dev ruff check --fix-only add2anki tests

# Verify code quality without modifying files
lint:
    uv run --dev ruff check add2anki tests

# Publish to PyPI
publish: clean
    uv build
    uv publish

# Run the application
run *ARGS:
    uv run python -m add2anki.cli {{ARGS}}

# Run tests with pytest
test *ARGS:
    uv run --dev pytest {{ARGS}}

# Run type checking with pyright
typecheck:
    uv run --dev pyright add2anki
