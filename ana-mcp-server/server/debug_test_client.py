

from fastapi.testclient import TestClient
from server.main import app

try:
    client = TestClient(app)
    print("TestClient instantiated successfully!")
except TypeError as e:
    print(f"TypeError when instantiating TestClient: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

