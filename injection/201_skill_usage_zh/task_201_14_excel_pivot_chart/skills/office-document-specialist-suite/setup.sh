#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "Task workspace dependencies are prepared by the benchmark setup."
echo "Do not create a virtual environment or install packages during the user task."
echo "Use:"
echo "  python ods.py template-report --output rapport.docx --title 'Q1 Analyse' --author 'Robert'"
