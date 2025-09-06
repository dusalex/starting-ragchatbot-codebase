#!/bin/bash
# Run type checking with mypy

echo "Running mypy..."
uv run mypy backend/ --ignore-missing-imports --show-error-codes

echo "Type checking complete!"