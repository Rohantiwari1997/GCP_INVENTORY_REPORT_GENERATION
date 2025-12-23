GCP_INVENTORY_REPORT_GENERATION

This project collects a GCP project's resource inventory using Cloud Asset, writes a single Excel workbook, and uploads it to a GCS bucket.

What is included
- `gcp_inventory/` — Python package with `inventory.py` entrypoint
- `requirements.txt` — runtime dependencies
- `setup.py` — package metadata and console entry
- `build_package.sh` — build wheel/sdist
- `install_and_run.sh` — helper installer + runner

Quick start (local machine)
---------------------------
1. Install prerequisites on your machine:

```bash
# on Debian/Ubuntu
sudo apt update && sudo apt install -y python3 python3-venv python3-pip
# or on macOS with Homebrew
brew install python
# Install Google Cloud SDK if you need gcloud/gsutil
# https://cloud.google.com/sdk/docs/install
```

2. Authenticate (preferred):

- For local development, either run `gcloud auth application-default login` or set `GOOGLE_APPLICATION_CREDENTIALS` to a service account key JSON.

3. Build and run:

```bash
./build_package.sh
./install_and_run.sh PROJECT_ID BUCKET_NAME --use-asset
# Example:
# ./install_and_run.sh my-project my-bucket --use-asset
```

Running on a new GCP VM (step-by-step)
-------------------------------------
1. Provision a VM (e.g., Debian/Ubuntu) and SSH into it.
2. Install Python 3.10+ and pip.
3. Install Google Cloud SDK or use the Python clients directly.
4. Preferred authentication on VM:
   - Best: Attach a Service Account to the VM with `roles/cloudasset.viewer` and `roles/storage.objectAdmin`.
     This avoids storing keys on disk and uses VM default credentials.
   - Alternative: Create a Service Account key and securely copy the JSON to the VM, then set:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

5. Copy this repository to the VM (git clone or rsync).
6. Run:

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install .
python3 -m gcp_inventory.inventory --project PROJECT_ID --bucket BUCKET_NAME --use-asset
```

Notes for large projects
- For very large projects use the Cloud Asset `export_assets` method to export to GCS and then process that file; this implementation collects via `search_all_resources()` and streams results into Excel which may be memory heavy for millions of resources.

Bitbucket runner / CI guidance
-----------------------------
You can run this in Bitbucket Pipelines or a self-hosted Bitbucket Runner. Two common approaches:

A) Use a service account JSON stored as a secured repository variable
- Add the base64-encoded JSON key as a secured repo variable (e.g., `GCP_SA_KEY_B64`).
- In pipeline, write it to a file, `export GOOGLE_APPLICATION_CREDENTIALS=/tmp/sa.json` and run the script.

Example pipeline step (conceptual):

```yaml
pipelines:
  default:
    - step:
        name: Run GCP inventory
        image: python:3.10
        script:
          - pip install -r requirements.txt
          - echo "$GCP_SA_KEY_B64" | base64 -d > /tmp/sa.json
          - export GOOGLE_APPLICATION_CREDENTIALS=/tmp/sa.json
          - python3 -m gcp_inventory.inventory --project $GCP_PROJECT --bucket $GCP_BUCKET --use-asset
```

B) Use Workload Identity / OIDC (recommended for security)
- Configure Bitbucket or runner to request short-lived credentials and exchange them for a GCP access token, or use a self-hosted runner on a VM with an attached service account.

Security notes
- Do not commit service account keys to source control.
- Prefer VM-attached service accounts or Workload Identity where possible.

Customization
- The code writes nested fields as JSON strings. For advanced use, extend `resources_to_excel()` to normalize nested schemas into columns.

Support
- If you want, I can add a `--export-gcs` mode that uses `AssetServiceClient.export_assets()` to write a single newline-delimited JSONL file to GCS for very large inventories.

