#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONPATH="$DIR/src" python3 -m emailsorter.cli gmail --config "$DIR/config.json" --dry-run "$@"
