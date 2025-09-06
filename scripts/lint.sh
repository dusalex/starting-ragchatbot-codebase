#!/bin/bash
# Run linting with flake8

echo "Running flake8..."
uv run flake8 backend/ --max-line-length=88 --extend-ignore=E203,W503

echo "Linting complete!"