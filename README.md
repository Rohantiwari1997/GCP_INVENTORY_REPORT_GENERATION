# GCP Inventory

This tool generates a GCP infrastructure inventory (several resource types) into an Excel file and uploads it to a Google Cloud Storage bucket.

## Prerequisites
- `gcloud` installed and authenticated (Application Default Credentials or `gcloud auth login`).
- Python 3.9+
- Dependencies installed: `pip install -r requirements.txt`

## Quick usage

1. Run the inventory script directly:

```bash
python3 inventory.py --project <PROJECT_ID> --bucket <GCS_BUCKET>
# Example: python3 inventory.py --project my-project --bucket my-bucket
```

Or use the helper script (which handles dependency installation):

```bash
./install_and_run.sh <PROJECT_ID> <GCS_BUCKET>
```

### Using Cloud Asset to collect all resources across locations

If you want to use Cloud Asset (Asset Inventory) to fetch all resources and their full metadata into a single Excel sheet, run with `--use-asset`:

```bash
# collect via Cloud Asset and upload to bucket
python3 inventory.py --project my-project --bucket my-bucket --use-asset
```

## Files
- `inventory.py` - Main script that collects resources and writes Excel.
- `requirements.txt` - Python requirements.
- `install_and_run.sh` - Helper script that installs dependencies and runs the inventory generation.
- `install_gcloud.sh` - Helper script to install Google Cloud SDK if missing.
- `setup_service_account.sh` - Helper script to create a Service Account with required permissions.

## Service Account Setup Utility

A helper script `setup_service_account.sh` is provided to automate the creation of the Service Account, assignment of necessary IAM roles, and key generation.

```bash
./setup_service_account.sh <PROJECT_ID> [SERVICE_ACCOUNT_NAME]
# Example: ./setup_service_account.sh my-project-id inventory-sa
```

This script will:
1. Create a Service Account (default: `inventory-sa`).
2. Grant the following roles: `roles/viewer`, `roles/cloudasset.viewer`, `roles/storage.objectAdmin`.
3. Enable the Cloud Asset API.
4. Generate and download the `gcp-inventory-sa-key.json` file.

## Service Account Authentication
If running in an environment without `gcloud` login (like a CI/CD pipeline), you can use a Service Account Key.
Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of your JSON key file:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/gcp-inventory-sa-key.json"
```

## Bitbucket Pipeline Setup

This repository includes a `bitbucket-pipelines.yml` configuration to run the inventory generation automatically.

### Requirements
1.  **Service Account Key**: Ensure `gcp-inventory-sa-key.json` is present in the root of the repository (or available in the build context).
2.  **Repository Variables**: Configure the following variables in your Bitbucket Repository Settings > Pipelines > Repository variables:
    *   `GCP_PROJECT_ID`: Comma-separated list of GCP Project IDs to scan (e.g., `project-a,project-b`).
    *   `GCS_BUCKET_NAME`: The GCS bucket name where the inventory Excel file will be uploaded.

The pipeline will:
1.  Install `gcloud` SDK.
2.  Authenticate using the Service Account key.
3.  Run the inventory script for the specified projects.
4.  Upload the results to the specified GCS bucket.

## Notes
- The script uses `gcloud` commands and Google Cloud libraries to collect resource lists. Ensure the user/service account running the script has adequate IAM permissions (e.g., Viewer, Cloud Asset Viewer).
