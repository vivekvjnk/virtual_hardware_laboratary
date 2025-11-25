

from typing import Any
from fastapi import HTTPException
import logging

logger = logging.getLogger("virtual_hardware_lab")

def jsonrpc_success(result: Any, id_val: Any):
    return {"jsonrpc": "2.0", "result": result, "id": id_val}

def jsonrpc_error(code: int, message: str, id_val: Any = None, data: Any = None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "error": err, "id": id_val}


def safe_join(base_dir: str, *paths: str) -> str:
    candidate = os.path.abspath(os.path.join(base_dir, *paths))
    base_dir_abs = os.path.abspath(base_dir)
    if not candidate.startswith(base_dir_abs):
        raise ValueError("Invalid path (possible path traversal).")
    return candidate

