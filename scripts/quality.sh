#!/bin/bash
# Run all quality checks

echo "==============================================="
echo "Running code quality checks..."
echo "==============================================="

echo "1. Formatting code..."
./scripts/format.sh

echo ""
echo "2. Running linter..."
./scripts/lint.sh

echo ""
echo "3. Running type checker..."
./scripts/typecheck.sh

echo ""
echo "==============================================="
echo "All quality checks complete!"
echo "==============================================="