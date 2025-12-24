#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <PROJECT_ID> [SERVICE_ACCOUNT_NAME]"
  echo "Example: $0 my-gcp-project inventory-sa"
  exit 1
fi

PROJECT_ID="$1"
SA_NAME="${2:-inventory-sa}" 
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="gcp-inventory-sa-key.json"

echo "Using Project: $PROJECT_ID"
echo "Service Account Name: $SA_NAME"
echo "Service Account Email: $SA_EMAIL"

# 1. Create the Service Account
echo "Creating Service Account..."
if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "Service Account $SA_EMAIL already exists."
else
    gcloud iam service-accounts create "$SA_NAME" \
    --description="Service Account for GCP Inventory Bitbucket Pipeline" \
    --display-name="GCP Inventory SA" \
    --project="$PROJECT_ID"
    echo "Service Account created."
fi

# 2. Grant Permissions
# We need Viewer (or specific list permissions), Cloud Asset Viewer, and Storage permissions.
ROLES=(
    "roles/viewer"
    "roles/cloudasset.viewer"
    "roles/storage.objectAdmin"
    "roles/serviceusage.serviceUsageConsumer"
)

echo "Granting permissions to $SA_EMAIL on project $PROJECT_ID..."
for role in "${ROLES[@]}"; do
    echo "Adding role: $role"
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$role" \
    --condition=None \
    --quiet >/dev/null
done

# 3. Enable necessary APIs (optional but good practice)
echo "Enabling Cloud Asset API..."
gcloud services enable cloudasset.googleapis.com --project="$PROJECT_ID"

# 4. Generate Key File
echo "Generating JSON key file..."
if [ -f "$KEY_FILE" ]; then
    echo "Key file $KEY_FILE already exists."
    BACKUP_FILE="${KEY_FILE}.bak.$(date +%s)"
    echo "Backing up existing key to $BACKUP_FILE..."
    mv "$KEY_FILE" "$BACKUP_FILE"
fi

gcloud iam service-accounts keys create "$KEY_FILE" \
    --iam-account="$SA_EMAIL" \
    --project="$PROJECT_ID"
echo "Key file downloaded to $(pwd)/$KEY_FILE"

echo "==================================================="
echo "Setup Complete!"
echo "1. The Service Account '$SA_EMAIL' is ready."
echo "2. Local key file: $KEY_FILE"
echo "3. Remember to: "
echo "   - Add '$KEY_FILE' to your Bitbucket Pipeline files (or base64 encode it into a variable)."
echo "   - If scanning OTHER projects, grant '$SA_EMAIL' the 'Viewer' and 'Cloud Asset Viewer' roles on those projects too."
echo "==================================================="
