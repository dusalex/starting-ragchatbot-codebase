#!/bin/bash
# Format code with black and isort

echo "Running black..."
uv run black .

echo "Running isort..."
uv run isort .

echo "Code formatting complete!"