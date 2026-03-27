from .object_storage import get_storage_client

def get_minio_client():
    """Backward compatibility bridge to unified storage client."""
    return get_storage_client()
