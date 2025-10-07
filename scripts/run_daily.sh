#!/usr/bin/env bash
set -e
# Update this path to your project root
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"
python -m app.pipeline > /tmp/ai_news_daily.log 2>&1
