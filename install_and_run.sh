#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -lt 2 ]; then
  echo "Usage: $0 PROJECT_ID GCS_BUCKET [--use-asset]"
  exit 1
fi
PROJECT=$1
BUCKET=$2
USE_ASSET_FLAG=${3:---use-asset}
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install .
python3 -m gcp_inventory.inventory --project "$PROJECT" --bucket "$BUCKET" $USE_ASSET_FLAG
