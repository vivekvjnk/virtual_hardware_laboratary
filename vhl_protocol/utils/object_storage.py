import os
import boto3
from botocore.client import Config
from typing import Optional, Union
import logging
from google.cloud import storage

logger = logging.getLogger(__name__)

class ObjectStorageClient:
    """Base class for object storage interactions."""
    def upload_file(self, file_path: str, object_key: str):
        raise NotImplementedError
    def download_file(self, object_key: str, download_path: str):
        raise NotImplementedError
    def object_exists(self, object_key: str) -> bool:
        raise NotImplementedError

class MinioClient(ObjectStorageClient):
    """MinIO implementation using boto3 (S3 API)."""
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
                logger.error(f"[MinioClient._ensure_bucket_exists] Failed to create bucket '{self.bucket_name}': {e}")
                # Don't raise here, might be a read-only client or BucketAlreadyOwnedByYou
                pass

    def upload_file(self, file_path: str, object_key: str):
        try:
            self.s3.upload_file(file_path, self.bucket_name, object_key)
            logger.info(f"[MinioClient.upload_file] Uploaded {file_path} to {object_key}")
        except Exception as e:
            logger.error(f"[MinioClient.upload_file] Failed to upload {file_path}: {e}")
            raise

    def download_file(self, object_key: str, download_path: str):
        try:
            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            self.s3.download_file(self.bucket_name, object_key, download_path)
            logger.info(f"[MinioClient.download_file] Downloaded {object_key} to {download_path}")
        except Exception as e:
            logger.error(f"[MinioClient.download_file] Failed to download {object_key}: {e}")
            raise

    def object_exists(self, object_key: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except Exception:
            return False

class GCSClient(ObjectStorageClient):
    """Google Cloud Storage implementation using native google-cloud-storage library."""
    def __init__(self):
        self.bucket_name = os.environ.get("GCS_BUCKET_NAME", "vhl-storage")
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.bucket_name)
        # Ensure bucket exists (optional, usually created beforehand in production)
        if not self.bucket.exists():
            logger.warning(f"[GCSClient] Bucket '{self.bucket_name}' does not exist.")

    def upload_file(self, file_path: str, object_key: str):
        try:
            blob = self.bucket.blob(object_key)
            blob.upload_from_filename(file_path)
            logger.info(f"[GCSClient.upload_file] Uploaded {file_path} to {object_key}")
        except Exception as e:
            logger.error(f"[GCSClient.upload_file] Failed to upload {file_path}: {e}")
            raise

    def download_file(self, object_key: str, download_path: str):
        try:
            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            blob = self.bucket.blob(object_key)
            blob.download_to_filename(download_path)
            logger.info(f"[GCSClient.download_file] Downloaded {object_key} to {download_path}")
        except Exception as e:
            logger.error(f"[GCSClient.download_file] Failed to download {object_key}: {e}")
            raise

    def object_exists(self, object_key: str) -> bool:
        try:
            blob = self.bucket.blob(object_key)
            return blob.exists()
        except Exception:
            return False

# Singleton instance
_client = None

def get_storage_client() -> ObjectStorageClient:
    """Return the appropriate storage client based on STORAGE_BACKEND environment variable."""
    global _client
    if _client is None:
        default_backend = "gcs" if "K_SERVICE" in os.environ else "minio"
        backend = os.environ.get("STORAGE_BACKEND", default_backend).lower()
        if backend == "gcs":
            _client = GCSClient()
            logger.info(f"[ObjectStorage] Using Google Cloud Storage backend (bucket: {_client.bucket_name})")
        else:
            _client = MinioClient()
            logger.info(f"[ObjectStorage] Using MinIO backend (bucket: {_client.bucket_name}, endpoint: {_client.endpoint_url})")
    return _client
