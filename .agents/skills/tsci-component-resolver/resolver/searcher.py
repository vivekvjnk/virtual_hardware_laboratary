"""
Searcher module: executes tsci search with strict timeouts, error trapping,
and intelligent ranking by package and stock.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ComponentMatch:
    lcsc: int | str
    mfr: str
    package: str
    description: str
    stock: int
    price: float | None
    is_preferred: bool
    source: str = "jlcpcb"


@dataclass
class SearchResult:
    query: str
    status: str  # "success", "not_found", "timeout", "network_error", "error"
    results: List[ComponentMatch]
    total_found: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


def _find_tsci() -> str:
    path = shutil.which("tsci")
    if path:
        return path
    for candidate in [
        "/opt/homebrew/bin/tsci",
        "/usr/local/bin/tsci",
        "/usr/bin/tsci",
    ]:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return "tsci"


def search_components(
    query: str,
    package_filter: Optional[str] = None,
    min_stock: int = 0,
    timeout_sec: float = 10.0,
    cwd: Optional[str] = None,
    tsci_bin: Optional[str] = None,
) -> SearchResult:
    """
    Executes 'tsci search <query> --json --jlcpcb' with timeout and structured parsing.
    """
    bin_path = tsci_bin or _find_tsci()
    cmd = [bin_path, "search", query, "--json", "--jlcpcb"]

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return SearchResult(
            query=query,
            status="timeout",
            results=[],
            total_found=0,
            error=f"Search timed out after {timeout_sec}s",
        )
    except Exception as e:
        return SearchResult(
            query=query,
            status="error",
            results=[],
            total_found=0,
            error=f"Failed to spawn tsci: {e}",
        )

    # Check for network connection failures
    combined_output = (proc.stdout + "\n" + proc.stderr).strip()
    if proc.returncode != 0:
        if "Unable to connect" in combined_output or "ENOTFOUND" in combined_output or "ECONNREFUSED" in combined_output:
            return SearchResult(
                query=query,
                status="network_error",
                results=[],
                total_found=0,
                error="Network connection failure: unable to reach JLCPCB/tscircuit registry API.",
            )
        return SearchResult(
            query=query,
            status="error",
            results=[],
            total_found=0,
            error=f"tsci search failed (exit code {proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}",
        )

    # Parse JSON output
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        if "No results found" in combined_output:
            return SearchResult(
                query=query,
                status="not_found",
                results=[],
                total_found=0,
            )
        return SearchResult(
            query=query,
            status="error",
            results=[],
            total_found=0,
            error=f"Failed to parse tsci JSON output: {proc.stdout[:200]}",
        )

    raw_results = data.get("results", [])
    matches: List[ComponentMatch] = []

    for item in raw_results:
        mfr = str(item.get("mfr", "")).strip()
        pkg = str(item.get("package", "")).strip()
        stock = int(item.get("stock", 0) or 0)
        lcsc = item.get("lcsc", "")
        desc = str(item.get("description", "")).strip()
        price = item.get("price")
        pref = bool(item.get("is_preferred", False))

        # Filter by min stock if requested
        if stock < min_stock:
            continue

        # Filter by package if requested (case-insensitive substring)
        if package_filter:
            clean_pkg = pkg.upper().replace("-", "").replace(" ", "")
            clean_filter = package_filter.upper().replace("-", "").replace(" ", "")
            if clean_filter not in clean_pkg:
                continue

        matches.append(
            ComponentMatch(
                lcsc=lcsc,
                mfr=mfr,
                package=pkg,
                description=desc,
                stock=stock,
                price=price,
                is_preferred=pref,
                source=item.get("source", "jlcpcb"),
            )
        )

    # Ranking:
    # 1. Exact match on mfr or C-part code
    # 2. Preferred parts
    # 3. In-stock (> 0)
    # 4. Stock descending
    q_norm = query.strip().upper()

    def rank_score(item: ComponentMatch) -> tuple:
        c_code = f"C{item.lcsc}".upper()
        exact_code = 1 if c_code == q_norm or str(item.lcsc) == q_norm else 0
        exact_mfr = 1 if item.mfr.upper() == q_norm else 0
        mfr_starts = 1 if item.mfr.upper().startswith(q_norm) else 0
        has_stock = 1 if item.stock > 0 else 0
        preferred = 1 if item.is_preferred else 0
        return (exact_code, exact_mfr, mfr_starts, preferred, has_stock, item.stock)

    matches.sort(key=rank_score, reverse=True)

    status = "success" if matches else "not_found"
    return SearchResult(
        query=query,
        status=status,
        results=matches,
        total_found=len(matches),
    )
