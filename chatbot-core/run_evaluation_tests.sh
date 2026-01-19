#!/bin/bash
# Quick script to run evaluation tests with virtual environment
# Usage: ./run_evaluation_tests.sh

set -e

echo "=========================================="
echo "Running Evaluation Tests"
echo "=========================================="
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "   Please create it first: python -m venv venv"
    exit 1
fi

# Activate virtual environment and run tests
source venv/bin/activate

echo "✓ Virtual environment activated"
echo ""

pytest tests/evaluation/ -v
