import os
import boto3
from botocore.client import Config
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class MinioClient:
    def __init__(self):
        self.endpoint_url = os.environ.get("MINIO_ENDPOINT_URL", "http://127.0.0.1:9000")
        self.access_key = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.environ.get("MINIO_SECRET_KEY", "supersecretpassword")
        self.bucket_name = os.environ.get("MINIO_BUCKET", "vhl")
        
        self.s3 = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1' # Default region for MinIO
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
        except Exception:
            try:
                self.s3.create_bucket(Bucket=self.bucket_name)
            except Exception as e:
                logger.error(f"Failed to create bucket '{self.bucket_name}': {e}")
                raise

    def upload_file(self, file_path: str, object_key: str):
        """Uploads a single file to the bucket."""
        try:
            self.s3.upload_file(file_path, self.bucket_name, object_key)
            logger.info(f"Uploaded {file_path} to {object_key}")
        except Exception as e:
            logger.error(f"Failed to upload {file_path}: {e}")
            raise

    def download_file(self, object_key: str, download_path: str):
        """Downloads a file from the bucket."""
        try:
            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            self.s3.download_file(self.bucket_name, object_key, download_path)
            logger.info(f"Downloaded {object_key} to {download_path}")
        except Exception as e:
            logger.error(f"Failed to download {object_key}: {e}")
            raise

    def object_exists(self, object_key: str) -> bool:
        """Check if an object exists in the bucket."""
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except Exception:
            return False

# Singleton instance
_client = None
def get_minio_client():
    global _client
    if _client is None:
        _client = MinioClient()
    return _client
