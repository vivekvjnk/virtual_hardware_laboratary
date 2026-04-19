#!/bin/bash

# Script to prepare the MinIO data directory with correct permissions and SELinux context

DIR=".object_store"

echo "Preparing MinIO data directory: $DIR"

# Create directory if it doesn't exist
if [ ! -d "$DIR" ]; then
    mkdir -p "$DIR"
    echo "Created directory $DIR"
else
    echo "Directory $DIR already exists"
fi

# Set ownership to current user
chown -R $(id -u):$(id -g) "$DIR"
echo "Set ownership to $(id -u):$(id -g)"

# Set permissions
chmod -R 775 "$DIR"
echo "Set permissions to 775"

# Set SELinux context for Docker access
if command -v chcon >/dev/null 2>&1; then
    sudo chcon -Rt svirt_sandbox_file_t "$DIR" 2>/dev/null || echo "Warning: Could not set SELinux context. You may need to run 'sudo chcon -Rt svirt_sandbox_file_t $DIR' manually."
    echo "Set SELinux context to svirt_sandbox_file_t"
else
    echo "chcon not available, skipping SELinux context setting"
fi

echo "MinIO data directory preparation complete."