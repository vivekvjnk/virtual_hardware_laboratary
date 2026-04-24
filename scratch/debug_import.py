import sys
import os

try:
    import vhl_common
    print(f"vhl_common location: {vhl_common.__file__}")
    from vhl_common import handle_errors
    print("Successfully imported handle_errors")
except Exception as e:
    print(f"Failed to import: {e}")
    import traceback
    traceback.print_exc()

print(f"Python path: {sys.path}")
