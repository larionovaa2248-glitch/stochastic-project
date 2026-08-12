#!/usr/bin/env bash
# One-command runner for macOS/Linux:  ./run.sh [--experiments] [--slides]
cd "$(dirname "$0")"
exec python3 run.py "$@"
