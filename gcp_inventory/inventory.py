"""GCP Inventory: collect resources via Cloud Asset, write Excel, upload to GCS.

Usage examples
--------------
python3 -m gcp_inventory.inventory --project PROJECT_ID --bucket BUCKET_NAME --use-asset

This module prefers Application Default Credentials. Set `GOOGLE_APPLICATION_CREDENTIALS` to
point at a service account JSON key, or run `gcloud auth application-default login`.
"""

from datetime import datetime
import json
import os
import argparse
import logging

import pandas as pd
from google.cloud import asset_v1
from google.protobuf.json_format import MessageToDict
from google.cloud import storage

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

INVALID_SHEET_CHARS = set(r":\\/*?[]")
MAX_SHEET_LEN = 31


def sanitize_sheet_name(name: str, used_names: set):
    # remove invalid chars
    out = ''.join(ch for ch in name if ch not in INVALID_SHEET_CHARS)
    out = out[:MAX_SHEET_LEN].strip() or 'sheet'
    base = out
    suffix = 1
    while out in used_names:
        tail = f"_{suffix}"
        out = (base[:MAX_SHEET_LEN - len(tail)] + tail).strip()
        suffix += 1
    used_names.add(out)
    return out


def collect_assets(project: str):
    """Collect resources via Cloud Asset API. Returns list of dicts."""
    client = asset_v1.AssetServiceClient()
    parent = f"projects/{project}"
    logger.info(f"Collecting Cloud Asset resources for {project}...")
    resources = []
    try:
        # search_all_resources returns an iterator of ResourceSearchResult
        for item in client.search_all_resources(request={"scope": parent}):
            # Convert protobuf to dict
            d = MessageToDict(item._pb)
            resources.append(d)
    except Exception as e:
        logger.error(f"Cloud Asset client error: {e}")
        raise
    logger.info(f"Collected {len(resources)} resources from Cloud Asset")
    return resources


def resources_to_excel(resources: list, out_path: str):
    """Write resources (list of dicts) to an Excel file with one sheet.

    For nested fields we keep JSON strings to avoid deeply normalized tables.
    """
    if not resources:
        # create empty sheet
        df = pd.DataFrame([{}])
    else:
        # flatten top-level keys; for nested values, JSON-serialize
        rows = []
        for r in resources:
            row = {}
            for k, v in r.items():
                if isinstance(v, (dict, list)):
                    row[k] = json.dumps(v, ensure_ascii=False)
                else:
                    row[k] = v
            rows.append(row)
        df = pd.DataFrame(rows)

    used = set()
    sheet_name = sanitize_sheet_name('assets', used)
    logger.info(f"Writing inventory to {out_path}")
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)


def upload_to_gcs(local_file: str, bucket_name: str, destination: str = None):
    destination = destination or os.path.basename(local_file)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination)
    logger.info(f"Uploading {local_file} to bucket {bucket_name}")
    blob.upload_from_filename(local_file)
    logger.info("Upload successful")


def main():
    parser = argparse.ArgumentParser(description="GCP Inventory to Excel and upload to GCS")
    parser.add_argument('--project', required=True)
    parser.add_argument('--bucket', required=True)
    parser.add_argument('--output', help='Local output filename (optional)')
    parser.add_argument('--use-asset', action='store_true', help='Use Cloud Asset to collect all resources')
    args = parser.parse_args()

    project = args.project
    bucket = args.bucket
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    out_file = args.output or f"gcp-inventory-{project}-{timestamp}.xlsx"

    if args.use_asset:
        resources = collect_assets(project)
    else:
        logger.error('Only --use-asset mode is implemented in this cleaned release. Use --use-asset.')
        return

    resources_to_excel(resources, out_file)
    upload_to_gcs(out_file, bucket)


if __name__ == '__main__':
    main()
