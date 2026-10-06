#!/bin/sh
# Local helper: uses the venv plus Homebrew's libraqm (correct Arabic/Urdu text)
# and expat (needed by Homebrew's Python 3.12 on this Mac).
cd "$(dirname "$0")"
export DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib:/opt/homebrew/lib
[ -f .env ] && set -a && . ./.env && set +a    # optional: ANTHROPIC_API_KEY=..., CHANNEL_TAG=...
exec .venv/bin/python -W ignore main.py "$@"
