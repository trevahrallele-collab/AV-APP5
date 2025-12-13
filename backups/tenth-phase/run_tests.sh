#!/bin/bash
echo "Running smoke tests..."
python smoke_test.py
if [ $? -eq 0 ]; then
    echo "✓ All tests passed!"
else
    echo "✗ Tests failed!"
    exit 1
fi