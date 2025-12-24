import sys

# Ensure importlib.metadata has `packages_distributions` on older Pythons
# Must be patched BEFORE importing pandas or other libs that might use it
try:
    import importlib.metadata as _importlib_metadata
    if not hasattr(_importlib_metadata, 'packages_distributions'):
        try:
            import importlib_metadata as _backport
            _importlib_metadata.packages_distributions = getattr(_backport, 'packages_distributions', None)
        except Exception:
            pass
except Exception:
    try:
        # fallback: ensure importlib.metadata maps to backport
        import importlib_metadata as _backport
        import sys as _sys
        _sys.modules['importlib.metadata'] = _backport
    except Exception:
        pass

import argparse
import subprocess
import json
import pandas as pd
from datetime import datetime
import os
from google.protobuf.json_format import MessageToDict


def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        # Don't treat API-specific errors as fatal here; return None so callers can decide
        # and avoid noisy stack traces.
        err = e.stderr or ''
        print(f"Command failed: {cmd}\n{err}", file=sys.stderr)
        return None


def is_service_enabled(project, service_name):
    """Return True if the given service (e.g. container.googleapis.com) is enabled for project."""
    out = run_cmd(f"gcloud services list --project={project} --enabled --format=json")
    if not out:
        return False
    try:
        services = json.loads(out)
        for s in services:
            # gcloud may return objects with different shapes; try common fields
            if s.get('name') == service_name or s.get('serviceName') == service_name:
                return True
            cfg = s.get('config') or {}
            if isinstance(cfg, dict) and cfg.get('name') == service_name:
                return True
        return False
    except Exception:
        # fallback to simple substring check
        return service_name in out


def gather_asset_resources(project):
    """Use the Python Cloud Asset client to search all resources in a project.

    Falls back to gcloud if the client library is not available.
    Returns a list of dicts.
    """
    try:
        from google.cloud import asset_v1
    except Exception:
        # fallback to gcloud CLI
        cmd = f"gcloud asset search-all-resources --scope=projects/{project} --project={project} --format=json"
        out = run_cmd(cmd)
        if out:
            try:
                return json.loads(out)
            except Exception:
                return []
        return []

    client = asset_v1.AssetServiceClient()
    scope = f"projects/{project}"
    resources = []
    try:
        # iterate with paging handled by the client
        for r in client.search_all_resources(scope=scope):
            try:
                d = MessageToDict(r._pb, preserving_proto_field_name=True)
            except Exception:
                # best effort conversion
                d = {}
                for field in r.DESCRIPTOR.fields:
                    val = getattr(r, field.name, None)
                    if val is not None:
                        d[field.name] = str(val)
            resources.append(d)
    except Exception as e:
        print(f"Cloud Asset client error: {e}", file=sys.stderr)
    return resources


def gather_resources(project):
    resources = {}

    # Compute instances
    out = run_cmd(f"gcloud compute instances list --project={project} --format=json")
    if out:
        try:
            resources['compute_instances'] = json.loads(out)
        except Exception:
            resources['compute_instances'] = []
    else:
        resources['compute_instances'] = []

    # GKE clusters - skip if the Kubernetes Engine API is not enabled to avoid noisy 403 errors
    if is_service_enabled(project, 'container.googleapis.com'):
        out = run_cmd(f"gcloud container clusters list --project={project} --format=json")
        if out:
            try:
                resources['gke_clusters'] = json.loads(out)
            except Exception:
                resources['gke_clusters'] = []
        else:
            resources['gke_clusters'] = []
    else:
        resources['gke_clusters'] = []
        print(f"Kubernetes Engine API not enabled for project {project}; skipping GKE cluster listing.")

    # Cloud Functions
    out = run_cmd(f"gcloud functions list --project={project} --format=json")
    if out:
        try:
            resources['cloud_functions'] = json.loads(out)
        except Exception:
            resources['cloud_functions'] = []
    else:
        resources['cloud_functions'] = []

    # Cloud SQL instances
    out = run_cmd(f"gcloud sql instances list --project={project} --format=json")
    if out:
        try:
            resources['sql_instances'] = json.loads(out)
        except Exception:
            resources['sql_instances'] = []
    else:
        resources['sql_instances'] = []

    # Storage buckets - use gcloud storage
    out = run_cmd(f"gcloud storage buckets list --project={project} --format=json")
    if out:
        try:
            # gcloud storage returns list of bucket objects
            resources['storage_buckets'] = json.loads(out)
        except Exception:
            resources['storage_buckets'] = []
    else:
        resources['storage_buckets'] = []

    return resources


def resources_to_excel(resources, output_file):
    def sanitize(name, used):
        # Excel sheet name rules: <=31 chars and cannot contain : \/ ? * [ ]
        invalid = ':\\/?*[]'
        s = ''.join('_' if c in invalid else c for c in name)
        s = s[:31]
        base = s
        i = 1
        while s in used or s == '':
            suffix = f"_{i}"
            # ensure total length <=31
            s = (base[:31 - len(suffix)] + suffix) if len(base) + len(suffix) > 31 else base + suffix
            i += 1
        used.add(s)
        return s

    used_names = set()
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for key, items in resources.items():
            try:
                if isinstance(items, list) and len(items) > 0 and isinstance(items[0], dict):
                    df = pd.json_normalize(items)
                else:
                    df = pd.DataFrame(items)
                sheet_name = sanitize(key, used_names)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            except Exception as e:
                print(f"Failed to write sheet {key}: {e}", file=sys.stderr)


def upload_to_gcs(local_file, bucket, destination_path=None):
    if not bucket:
        print("No bucket provided, skipping upload.")
        return False
    dest = f"gs://{bucket}/"
    if destination_path:
        dest = f"gs://{bucket}/{destination_path}"
    # Use gcloud storage cp
    cmd = f"gcloud storage cp {local_file} {dest}"
    out = run_cmd(cmd)
    return out is not None


def main():
    parser = argparse.ArgumentParser(description='Generate GCP infra inventory and upload to GCS')
    parser.add_argument('--project', '-p', required=False, help='GCP project id (or comma separated list)')
    parser.add_argument('--bucket', '-b', required=False, help='GCS bucket name to upload the Excel file')
    parser.add_argument('--output', '-o', required=False, help='Local output filename (default inventory_TIMESTAMP.xlsx)')
    parser.add_argument('--use-asset', action='store_true', help='Use Cloud Asset (gcloud asset) to collect resources across locations')
    args = parser.parse_args()

    project = args.project or os.environ.get('GOOGLE_CLOUD_PROJECT')
    if not project:
        print('Project not provided via --project or GOOGLE_CLOUD_PROJECT environment variable', file=sys.stderr)
        sys.exit(2)

    projects = [p.strip() for p in project.split(',') if p.strip()]

    combined = {}
    for p in projects:
        print(f"Gathering resources for project: {p}")
        if args.use_asset:
            assets = gather_asset_resources(p)
            combined_key = f"{p}::asset_resources"
            combined[combined_key] = assets
        else:
            res = gather_resources(p)
            # prefix keys with project name
            for k, v in res.items():
                combined_key = f"{p}::{k}"
                combined[combined_key] = v

    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    output = args.output or f"gcp-inventory-{projects[0]}-{ts}.xlsx"

    print(f"Writing inventory to {output}")
    resources_to_excel(combined, output)

    if args.bucket:
        print(f"Uploading {output} to bucket {args.bucket}")
        ok = upload_to_gcs(output, args.bucket)
        if ok:
            print("Upload successful")
        else:
            print("Upload failed", file=sys.stderr)


if __name__ == '__main__':
    main()
