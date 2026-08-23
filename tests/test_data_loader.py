"""
test_data_loader.py — unit tests for backend/data_loader.py (task 2.2)
"""
import pandas as pd
import pytest
from zoneinfo import ZoneInfo

from backend.data_loader import load_data, SNAPSHOT_TIME, DataStore


def test_snapshot_time_exact_value():
    """SNAPSHOT_TIME must be 2026-08-16T11:00:00+05:30 exactly."""
    assert str(SNAPSHOT_TIME) == "2026-08-16 11:00:00+05:30"


def test_snapshot_time_is_timezone_aware():
    assert SNAPSHOT_TIME.tzinfo is not None


def test_datastore_loads(data_store):
    """DataStore loads without error and contains all three sheets."""
    assert isinstance(data_store, DataStore)
    assert len(data_store.accounts) == 4
    assert len(data_store.orders) == 6
    assert len(data_store.tickets) == 7


def test_order_dates_are_timezone_aware(data_store):
    """Datetime columns in orders must be timezone-aware after loading."""
    col = data_store.orders["booked_at"].dropna()
    assert col.dt.tz is not None, "booked_at should be timezone-aware"


def test_ticket_dates_are_timezone_aware(data_store):
    col = data_store.tickets["created_at"].dropna()
    assert col.dt.tz is not None, "created_at should be timezone-aware"


def test_accounts_required_columns(data_store):
    required = {"account_id", "account_name", "plan", "status", "csm"}
    assert required.issubset(set(data_store.accounts.columns))


def test_orders_required_columns(data_store):
    required = {"order_id", "account_id", "carrier", "status",
                "booked_at", "pickup_window_end", "shipment_fee_inr",
                "carrier_fault", "customer_fault"}
    assert required.issubset(set(data_store.orders.columns))


def test_tickets_required_columns(data_store):
    required = {"ticket_id", "account_id", "created_at", "status", "subject"}
    assert required.issubset(set(data_store.tickets.columns))


def test_snapshot_time_not_dynamic():
    """Importing SNAPSHOT_TIME twice returns the same object (it's a constant)."""
    from backend.data_loader import SNAPSHOT_TIME as T1
    from backend.data_loader import SNAPSHOT_TIME as T2
    assert T1 is T2
