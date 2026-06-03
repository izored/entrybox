#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

python -c "import fastapi" 2>/dev/null || {
  echo "Installing dependencies..."
  pip install -r requirements.txt
}

echo ""
echo "EntryBox running at http://localhost:3859"
echo "Press Ctrl+C to stop."
echo ""

python -m uvicorn app.main:app --host 127.0.0.1 --port 3859 --reload
