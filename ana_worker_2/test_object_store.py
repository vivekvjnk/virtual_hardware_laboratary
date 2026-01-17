import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add the parent directory to sys.path to allow importing ana_worker_2
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ana_worker_2.utils.object_store import MinioObjectStore

class TestMinioObjectStore(unittest.TestCase):
    @patch('boto3.client')
    def setUp(self, mock_boto_client):
        self.mock_s3 = MagicMock()
        mock_boto_client.return_value = self.mock_s3
        # The __init__ calls _ensure_bucket_exists, which calls head_bucket
        self.store = MinioObjectStore(
            endpoint_url="http://127.0.0.1:9000",
            access_key="test",
            secret_key="test",
            bucket_name="vhl"
        )

    def test_ensure_bucket_exists_creates_if_missing(self):
        # Reset mock to clear calls from __init__
        self.mock_s3.head_bucket.side_effect = Exception("Not found")
        self.store._ensure_bucket_exists()
        self.mock_s3.create_bucket.assert_called_with(Bucket="vhl")

    @patch('os.listdir')
    @patch('os.path.exists')
    @patch('os.path.isfile')
    def test_upload_tsx_files(self, mock_isfile, mock_exists, mock_listdir):
        mock_exists.return_value = True
        mock_listdir.return_value = ['file1.tsx', 'file2.txt', 'file3.tsx']
        mock_isfile.return_value = True

        mapping = self.store.upload_tsx_files("/fake/path")

        self.assertEqual(len(mapping), 2)
        self.assertIn('file1.tsx', mapping)
        self.assertIn('file3.tsx', mapping)
        # upload_file should be called for each .tsx file
        self.assertEqual(self.mock_s3.upload_file.call_count, 2)

    def test_get_object_url(self):
        url = self.store.get_object_url("test.tsx")
        self.assertEqual(url, "http://127.0.0.1:9000/vhl/test.tsx")

if __name__ == '__main__':
    unittest.main()
