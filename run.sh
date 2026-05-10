#!/usr/bin/env bash
# TraceCore launcher
cd "$(dirname "$0")"

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python3 src/main.py "$@"
