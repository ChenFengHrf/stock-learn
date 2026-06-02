#!/usr/bin/env bash
set -euo pipefail

COURSE_DIR="${1:-/Users/renfenghuang/Documents/Codex/2026-05-31/https-app7r5sbqh74475-h5-xet-pomoho-com/outputs/建立交易体系-离线包}"
DB_PATH="${2:-data/private/stock_learn.sqlite}"

stock-learn ingest-course "$COURSE_DIR" --db "$DB_PATH"

