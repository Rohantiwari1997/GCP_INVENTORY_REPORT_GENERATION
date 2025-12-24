#!/usr/bin/env bash
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <PROJECT_ID[,PROJECT_ID2,...]> <GCS_BUCKET>"
  exit 1
fi

PROJECTS="$1"
BUCKET="$2"

cd "$(dirname "$0")"

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# Run the inventory script directly
# Run the inventory script directly
python3 inventory.py --project "$PROJECTS" --bucket "$BUCKET" --use-asset
