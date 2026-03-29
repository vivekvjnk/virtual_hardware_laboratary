import os
import logging
from typing import Dict, Optional, Union
from vhl_protocol.utils.object_storage import get_storage_client

logger = logging.getLogger(__name__)

class MinioObjectStore:
    """
    Bridge class that provides convenience methods for object storage
    using the unified ObjectStorageClient.
    """
    def __init__(self, endpoint_url: Optional[str] = None):
        """
        Initialize using the unified storage client.
        endpoint_url is kept for backward compatibility but ignored if STORAGE_BACKEND is set.
        """
        self.storage_client = get_storage_client()
        self.bucket_name = getattr(self.storage_client, "bucket_name", "vhl-storage")
        # Fallback for URL generation in MinIO
        self.endpoint_url = endpoint_url or os.environ.get("MINIO_ENDPOINT_URL", "http://127.0.0.1:9000")

    def upload_tsx_files(self, directory_path: str) -> Dict[str, str]:
        """
        Uploads all .tsx files in the directory to the bucket.
        Returns a mapping of filename to its object key.
        """
        mapping = {}
        if not os.path.exists(directory_path):
            logger.warning(f"[MinioObjectStore.upload_tsx_files] Directory {directory_path} does not exist.")
            return mapping

        for filename in os.listdir(directory_path):
            if filename.endswith(".tsx"):
                file_path = os.path.join(directory_path, filename)
                if os.path.isdir(file_path):
                    continue
                object_key = filename
                try:
                    self.storage_client.upload_file(file_path, object_key)
                    mapping[filename] = object_key
                    logger.info(f"[MinioObjectStore.upload_tsx_files] Uploaded {filename} to {object_key}")
                except Exception as e:
                    logger.error(f"[MinioObjectStore.upload_tsx_files] Failed to upload {filename}: {e}")
        
        return mapping

    def upload_file(self, file_path: str, object_key: Optional[str] = None) -> str:
        """
        Uploads a single file to the bucket.
        Returns the object key.
        """
        if object_key is None:
            object_key = os.path.basename(file_path)
        
        try:
            self.storage_client.upload_file(file_path, object_key)
            logger.info(f"[MinioObjectStore.upload_file] Uploaded {file_path} to {object_key}")
            return object_key
        except Exception as e:
            logger.error(f"[MinioObjectStore.upload_file] Failed to upload {file_path}: {e}")
            raise

    def download_file(self, object_key: str, download_path: str):
        """
        Downloads a file from the bucket.
        """
        try:
            self.storage_client.download_file(object_key, download_path)
            logger.info(f"[MinioObjectStore.download_file] Downloaded {object_key} to {download_path}")
        except Exception as e:
            logger.error(f"[MinioObjectStore.download_file] Failed to download {object_key}: {e}")
            raise

    def get_object_url(self, object_key: str) -> str:
        """
        Returns the URL for the object.
        """
        # For GCS, this would need a different URL format if used for public access
        if self.storage_client.__class__.__name__ == "GCSClient":
            return f"https://storage.googleapis.com/{self.bucket_name}/{object_key}"
        return f"{self.endpoint_url}/{self.bucket_name}/{object_key}"
