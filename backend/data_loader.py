"""
data_loader.py — loads ParcelPilot_Assessment_Data.xlsx into typed in-memory DataFrames.

SNAPSHOT_TIME is the authoritative "now" for all time-based calculations.
It is a hardcoded constant — NEVER replace with datetime.now().
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

logger = logging.getLogger(__name__)

# ── Authoritative snapshot time ──────────────────────────────────────────────
# Source: README sheet of ParcelPilot_Assessment_Data.xlsx
# This constant is the single source of truth for "now" across the entire system.
# Import it from here — never redefine it in another module.
_IST = ZoneInfo("Asia/Kolkata")
SNAPSHOT_TIME = pd.Timestamp("2026-08-16 11:00:00", tz=_IST)


@dataclass
class DataStore:
    accounts: pd.DataFrame
    orders: pd.DataFrame
    tickets: pd.DataFrame
    snapshot_time: pd.Timestamp


def load_data(xlsx_path: Path) -> DataStore:
    """
    Parse all sheets of the assessment XLSX into typed DataFrames.
    Logs a descriptive error (does NOT raise) for any record that fails schema checks.
    """
    xl = pd.ExcelFile(xlsx_path)

    accounts = xl.parse("accounts")
    orders = xl.parse(
        "orders",
        parse_dates=[
            "booked_at",
            "pickup_window_start",
            "pickup_window_end",
            "pickup_actual_at",
            "cancellation_requested_at",
        ],
    )
    tickets = xl.parse(
        "tickets",
        parse_dates=["created_at", "last_customer_message_at"],
    )

    # Make datetime columns timezone-aware (IST) where they are tz-naive after parse
    def _localize(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        for col in cols:
            if col in df.columns and pd.api.types.is_datetime64_any_dtype(df[col]):
                if df[col].dt.tz is None:
                    df[col] = df[col].dt.tz_localize(_IST)
        return df

    orders = _localize(
        orders,
        ["booked_at", "pickup_window_start", "pickup_window_end",
         "pickup_actual_at", "cancellation_requested_at"],
    )
    tickets = _localize(tickets, ["created_at", "last_customer_message_at"])

    # Schema validation — log errors, do not raise
    _validate_accounts(accounts)
    _validate_orders(orders)
    _validate_tickets(tickets)

    return DataStore(
        accounts=accounts,
        orders=orders,
        tickets=tickets,
        snapshot_time=SNAPSHOT_TIME,
    )


# ── Schema validators ─────────────────────────────────────────────────────────

def _validate_accounts(df: pd.DataFrame) -> None:
    required = {"account_id", "account_name", "plan", "status", "csm"}
    _check_required_columns(df, required, "accounts")


def _validate_orders(df: pd.DataFrame) -> None:
    required = {"order_id", "account_id", "carrier", "status",
                "booked_at", "pickup_window_start", "pickup_window_end",
                "shipment_fee_inr", "carrier_fault", "customer_fault"}
    _check_required_columns(df, required, "orders")


def _validate_tickets(df: pd.DataFrame) -> None:
    required = {"ticket_id", "account_id", "created_at", "status", "subject"}
    _check_required_columns(df, required, "tickets")


def _check_required_columns(
    df: pd.DataFrame, required: set[str], table_name: str
) -> None:
    missing = required - set(df.columns)
    if missing:
        logger.error(
            "Schema validation failed for table '%s': missing columns %s",
            table_name,
            sorted(missing),
        )
