#!/bin/bash
set -e

# Function to check if command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

if command_exists gcloud; then
  echo "gcloud is already installed."
  gcloud --version
  exit 0
fi

echo "Installing Google Cloud SDK..."

# Determine if we need sudo
sudo_cmd=""
if [ "$(id -u)" != "0" ] && command_exists sudo; then
    sudo_cmd="sudo"
fi

if command_exists apt-get; then
    # Debian/Ubuntu based installation
    $sudo_cmd apt-get update
    $sudo_cmd apt-get install -y apt-transport-https ca-certificates gnupg curl

    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | $sudo_cmd tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
    
    # Modern approach: dearmor the key and save it directly, avoiding apt-key
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | $sudo_cmd gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
    
    $sudo_cmd apt-get update
    $sudo_cmd apt-get install -y google-cloud-sdk
else
    # Generic Linux installation
    echo "apt-get not found, attempting generic installation..."
    if [ -f google-cloud-cli-linux-x86_64.tar.gz ]; then
        rm google-cloud-cli-linux-x86_64.tar.gz
    fi
    curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz
    tar -xf google-cloud-cli-linux-x86_64.tar.gz
    ./google-cloud-sdk/install.sh --quiet
    
    # Add to path for this session
    if [ -f "./google-cloud-sdk/path.bash.inc" ]; then
        source ./google-cloud-sdk/path.bash.inc
    fi
    
    # Try to link it commonly if possible, or just rely on path
    export PATH=$PATH:$(pwd)/google-cloud-sdk/bin
    
    # Symlink to /usr/local/bin to make it available globally/in future steps
    if command_exists sudo; then
        sudo ln -sf "$(pwd)/google-cloud-sdk/bin/gcloud" /usr/local/bin/gcloud
    else
        ln -sf "$(pwd)/google-cloud-sdk/bin/gcloud" /usr/local/bin/gcloud 2>/dev/null || echo "Could not symlink gcloud, strictly relying on PATH export."
    fi
fi

echo "gcloud installation complete."
gcloud --version
