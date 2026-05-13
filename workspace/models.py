from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class FileChange:
    file_path: str
    change_type: str  # ADDED / MODIFIED / DELETED

@dataclass
class Artifact:
    commit_hash: str
    parent_commit_hash: Optional[str]
    changes: List[FileChange]

@dataclass
class Operation:
    module_name: str
    op_name: str           # ARCHY / LIBRARIAN / ANA
    status: str            # SUCCESS / PARTIAL / FAILURE / ACCEPT / REJECT
    payload: Optional[Dict]
    timestamp: str
    artifact: Artifact
