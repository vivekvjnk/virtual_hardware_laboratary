import json
import subprocess
from unittest.mock import patch, MagicMock
import pytest
from resolver.searcher import search_components, SearchResult


MOCK_NE555_JSON = json.dumps({
    "query": "NE555",
    "results": [
        {
            "source": "jlcpcb",
            "lcsc": 7593,
            "mfr": "NE555DR",
            "package": "SOIC-8",
            "is_preferred": True,
            "description": "Timer IC SOIC-8",
            "stock": 200000,
            "price": 0.12
        },
        {
            "source": "jlcpcb",
            "lcsc": 105643,
            "mfr": "NE555PWR",
            "package": "TSSOP-8",
            "is_preferred": False,
            "description": "Timer IC TSSOP-8",
            "stock": 10000,
            "price": 0.22
        },
        {
            "source": "jlcpcb",
            "lcsc": 46749,
            "mfr": "NE555P",
            "package": "DIP-8",
            "is_preferred": False,
            "description": "Timer IC DIP-8",
            "stock": 0,
            "price": 0.30
        }
    ]
})


def test_search_components_success():
    mock_proc = MagicMock(returncode=0, stdout=MOCK_NE555_JSON, stderr="")
    with patch("subprocess.run", return_value=mock_proc):
        res = search_components("NE555")

    assert res.status == "success"
    assert res.total_found == 3
    assert res.results[0].mfr == "NE555DR"
    assert res.results[0].is_preferred is True


def test_search_components_package_filter():
    mock_proc = MagicMock(returncode=0, stdout=MOCK_NE555_JSON, stderr="")
    with patch("subprocess.run", return_value=mock_proc):
        res = search_components("NE555", package_filter="TSSOP-8")

    assert res.status == "success"
    assert res.total_found == 1
    assert res.results[0].package == "TSSOP-8"
    assert res.results[0].mfr == "NE555PWR"


def test_search_components_stock_filter():
    mock_proc = MagicMock(returncode=0, stdout=MOCK_NE555_JSON, stderr="")
    with patch("subprocess.run", return_value=mock_proc):
        res = search_components("NE555", min_stock=50000)

    assert res.status == "success"
    assert res.total_found == 1
    assert res.results[0].stock == 200000


def test_search_components_not_found():
    empty_json = json.dumps({"query": "UNKNOWN", "results": []})
    mock_proc = MagicMock(returncode=0, stdout=empty_json, stderr="")
    with patch("subprocess.run", return_value=mock_proc):
        res = search_components("UNKNOWN")

    assert res.status == "not_found"
    assert res.total_found == 0


def test_search_components_timeout():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["tsci"], timeout=10.0)):
        res = search_components("NE555", timeout_sec=10.0)

    assert res.status == "timeout"
    assert "timed out" in res.error


def test_search_components_network_error():
    mock_proc = MagicMock(returncode=1, stdout="", stderr="Failed to search: Unable to connect. Is the computer able to access the url?")
    with patch("subprocess.run", return_value=mock_proc):
        res = search_components("NE555")

    assert res.status == "network_error"
    assert "Network connection failure" in res.error
