#!/usr/bin/env python3
"""
Bucket initialization script for both MinIO and GCS.

This script ensures that the required bucket exists for the configured storage backend.
It should be run during application initialization or deployment setup.

Usage:
    python scripts/initialize_bucket.py

Environment Variables:
    STORAGE_BACKEND: 'minio' or 'gcs' (default: 'minio')
    OBJECT_STORE_BUCKET: Bucket name (default: 'vhl' for MinIO, 'vhl-storage' for GCS)
    
    MinIO specific:
        MINIO_ENDPOINT: MinIO endpoint URL (default: 'http://minio:9000')
        MINIO_ROOT_USER: MinIO root username (default: 'minioadmin')
        MINIO_ROOT_PASSWORD: MinIO root password (default: 'supersecretpassword')
    
    GCS specific:
        GCP_PROJECT: GCP project ID
        GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON file
"""

import os
import sys
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_minio_bucket() -> bool:
    """Initialize MinIO bucket."""
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        logger.error("boto3 not installed. Install with: pip install boto3")
        return False
    
    bucket_name = os.getenv("OBJECT_STORE_BUCKET", "vhl")
    endpoint = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
    access_key = os.getenv("MINIO_ROOT_USER", "minioadmin")
    secret_key = os.getenv("MINIO_ROOT_PASSWORD", "supersecretpassword")
    
    try:
        logger.info(f"Connecting to MinIO at {endpoint}...")
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )
        
        # Check if bucket exists
        try:
            s3.head_bucket(Bucket=bucket_name)
            logger.info(f"✓ MinIO bucket '{bucket_name}' already exists")
            return True
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                # Bucket doesn't exist, create it
                logger.info(f"Creating MinIO bucket '{bucket_name}'...")
                s3.create_bucket(Bucket=bucket_name)
                logger.info(f"✓ Created MinIO bucket '{bucket_name}'")
                return True
            else:
                raise
    except Exception as e:
        logger.error(f"✗ Failed to initialize MinIO bucket: {e}")
        return False


def initialize_gcs_bucket() -> bool:
    """Initialize GCS bucket."""
    try:
        from google.cloud import storage
        from google.api_core.exceptions import NotFound, AlreadyExists, Forbidden
    except ImportError:
        logger.error("google-cloud-storage not installed. Install with: pip install google-cloud-storage")
        return False
    
    bucket_name = os.getenv("OBJECT_STORE_BUCKET", "vhl-storage")
    gcp_project = os.getenv("GCP_PROJECT")
    
    if not gcp_project:
        logger.warning("GCP_PROJECT not set. Attempting to use application default credentials...")
    
    try:
        logger.info(f"Connecting to GCS project '{gcp_project}'...")
        client = storage.Client(project=gcp_project)
        bucket = client.bucket(bucket_name)
        
        if bucket.exists():
            logger.info(f"✓ GCS bucket '{bucket_name}' already exists")
            return True
        else:
            logger.info(f"Creating GCS bucket '{bucket_name}'...")
            bucket.create()
            logger.info(f"✓ Created GCS bucket '{bucket_name}'")
            return True
    except Forbidden as e:
        logger.error(f"✗ Permission denied. Check GCP_PROJECT and credentials: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Failed to initialize GCS bucket: {e}")
        return False


def main() -> int:
    """Main initialization routine."""
    backend = os.getenv("STORAGE_BACKEND", "minio").lower()
    
    logger.info(f"Initializing storage backend: {backend}")
    
    if backend == "minio":
        success = initialize_minio_bucket()
    elif backend == "gcs":
        success = initialize_gcs_bucket()
    else:
        logger.error(f"✗ Unknown storage backend: {backend}")
        return 1
    
    if success:
        logger.info("✓ Bucket initialization successful")
        return 0
    else:
        logger.error("✗ Bucket initialization failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
