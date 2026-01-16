import os
import boto3
from botocore.client import Config
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class MinioObjectStore:
    def __init__(self, endpoint_url: str = "http://127.0.0.1:9000", 
                 access_key: str = "minioadmin", 
                 secret_key: str = "minioadmin", 
                 bucket_name: str = "vhl"):
        """
        Initialize Minio Object Store client using S3 compatible API.
        """
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name
        self.s3 = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """
        Checks if the bucket exists, creates it if it doesn't.
        """
        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket '{self.bucket_name}' already exists.")
        except Exception:
            logger.info(f"Bucket '{self.bucket_name}' does not exist. Creating...")
            try:
                self.s3.create_bucket(Bucket=self.bucket_name)
            except Exception as e:
                logger.error(f"Failed to create bucket '{self.bucket_name}': {e}")
                raise

    def upload_tsx_files(self, directory_path: str) -> Dict[str, str]:
        """
        Uploads all .tsx files in the directory to the bucket.
        Returns a mapping of filename to its object key.
        """
        mapping = {}
        if not os.path.exists(directory_path):
            logger.warning(f"Directory {directory_path} does not exist.")
            return mapping

        for filename in os.listdir(directory_path):
            if filename.endswith(".tsx"):
                file_path = os.path.join(directory_path, filename)
                if os.path.isdir(file_path):
                    continue
                object_key = filename
                try:
                    self.s3.upload_file(file_path, self.bucket_name, object_key)
                    mapping[filename] = object_key
                    logger.info(f"Uploaded {filename} to {self.bucket_name}/{object_key}")
                except Exception as e:
                    logger.error(f"Failed to upload {filename}: {e}")
        
        return mapping

    def get_object_url(self, object_key: str) -> str:
        """
        Returns the URL for the object.
        """
        return f"{self.endpoint_url}/{self.bucket_name}/{object_key}"
