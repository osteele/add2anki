# Justfile for langki project

# Install dependencies
setup:
    uv sync

# Default recipe to run when just is called without arguments
default:
    @just --list

# Format code with black and ruff
fmt:
    uv run black .
    uv run ruff --fix .

# Run type checking with mypy
tc:
    uv run pyright langki

# Run tests with pytest
test *ARGS:
    uv run pytest {{ARGS}}

# Run all checks: formatting, type checking, and tests
check: fmt tc test
    @echo "All checks passed!"

# Run the application
run *ARGS:
    uv run python -m langki.cli {{ARGS}}
