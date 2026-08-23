"""
conftest.py — shared fixtures for all backend unit tests.
"""
import sys
from pathlib import Path

# Ensure parcelpilot-agent/ is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
from zoneinfo import ZoneInfo

from backend.data_loader import load_data, SNAPSHOT_TIME, DataStore


_IST = ZoneInfo("Asia/Kolkata")
_SOURCES = Path(__file__).parent.parent / "sources"
_XLSX = _SOURCES / "ParcelPilot_Assessment_Data.xlsx"


@pytest.fixture(scope="session")
def data_store() -> DataStore:
    """Real DataStore loaded from the XLSX once per test session."""
    return load_data(_XLSX)


@pytest.fixture(scope="session")
def collection():
    """Real ChromaDB collection built once per test session."""
    from backend.vector_store import init_vector_store
    return init_vector_store(_SOURCES)
