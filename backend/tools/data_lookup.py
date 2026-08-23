"""
data_lookup.py — Tool 2: structured data queries over accounts, orders, and tickets.

Access control is enforced HERE in Python — not in the LLM system prompt.
CSM-only fields (premium_support, notes) are stripped from the payload for
support_agent sessions before the model ever sees the data.

SNAPSHOT_TIME is imported from data_loader — never redefined here.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import pandas as pd

from backend.data_loader import SNAPSHOT_TIME, DataStore

logger = logging.getLogger(__name__)

CSM_ONLY_FIELDS = ["premium_support", "notes"]

ACCOUNT_SLA: dict[str, dict] = {
    "ACCT-001": {
        "P1": timedelta(minutes=15), "P2": timedelta(hours=1), "P3": timedelta(hours=8),
        "source": "05_Northstar_Logistics_Enterprise_Agreement.pdf §1", "coverage": "24x7",
    },
    "ACCT-002": {
        "P1": timedelta(hours=2), "P2": timedelta(hours=4), "P3": timedelta(days=2),
        "source": "06_LumenWorks_Service_Agreement.pdf §1",
        "coverage": "business hours only, no weekend/after-hours",
    },
    "ACCT-003": {
        "P1": timedelta(hours=4), "P2": timedelta(days=1), "P3": timedelta(days=2),
        "source": "01_Support_Policy_v3_CURRENT.pdf §3 (Standard plan)", "coverage": "business hours",
    },
    "ACCT-004": {
        "P1": timedelta(minutes=30), "P2": timedelta(hours=2), "P3": timedelta(days=1),
        "source": "01_Support_Policy_v3_CURRENT.pdf §3 (Enterprise plan)", "coverage": "24x7",
        "note": "No custom agreement in pack — standard Enterprise policy applies. "
                "Do NOT apply ACCT-001 Northstar's 15-min contractual P1 target here.",
    },
}

KI_PATTERNS = [
    {"ki_id": "KI-208", "keywords": ["bulk upload", "csv", "upload fail", "row"],
     "description": "Intermittent bulk upload failures above ~3,000 rows (product limit 5,000 rows)"},
    {"ki_id": "KI-211", "keywords": ["swiftship", "booked", "webhook", "pickup delay", "driver"],
     "description": "SwiftShip webhook delay up to 20 min; BOOKED may persist after physical pickup"},
]


def lookup(query_type: str, filters: dict, current_user_role: str, data_store: DataStore) -> dict[str, Any]:
    fields_withheld: list[str] = []
    if query_type == "account":
        results, fields_withheld = _query_accounts(filters, current_user_role, data_store)
    elif query_type == "order":
        results = _query_orders(filters, data_store)
    elif query_type == "ticket":
        results = _query_tickets(filters, data_store)
    elif query_type == "sla_check":
        results = _sla_check(filters, data_store)
    elif query_type == "credit_calc":
        results = _credit_calc(filters, data_store)
    elif query_type == "proactive_sweep":
        results = _proactive_sweep(data_store)
    else:
        logger.warning("Unknown query_type: %s", query_type)
        results = []
    return {"results": results, "snapshot_time": SNAPSHOT_TIME.isoformat(),
            "access_granted": True, "fields_withheld": fields_withheld}


def _query_accounts(filters: dict, role: str, data_store: DataStore) -> tuple[list[dict], list[str]]:
    df = data_store.accounts.copy()
    for key, val in filters.items():
        if key in df.columns:
            df = df[df[key] == val]
    records = _df_to_records(df)
    fields_withheld: list[str] = []
    if role == "support_agent":
        stripped = []
        for rec in records:
            stripped.append({k: v for k, v in rec.items() if k not in CSM_ONLY_FIELDS})
        records = stripped
        fields_withheld = [f for f in CSM_ONLY_FIELDS if f in data_store.accounts.columns.tolist()]
    return records, fields_withheld


def _query_orders(filters: dict, data_store: DataStore) -> list[dict]:
    df = data_store.orders.copy()
    for key, val in filters.items():
        if key in df.columns:
            df = df[df[key] == val]
    return _df_to_records(df)


def _query_tickets(filters: dict, data_store: DataStore) -> list[dict]:
    df = data_store.tickets.copy()
    for key, val in filters.items():
        if key in df.columns:
            df = df[df[key] == val]
    return _df_to_records(df)


def _sla_check(filters: dict, data_store: DataStore) -> list[dict]:
    ticket_id = filters.get("ticket_id")
    account_id = filters.get("account_id")
    df = data_store.tickets
    if ticket_id:
        row = df[df["ticket_id"] == ticket_id]
    elif account_id:
        row = df[(df["account_id"] == account_id) & (df["status"] == "open")]
    else:
        row = df
    records = _df_to_records(row)
    results = []
    for rec in records:
        t_account_id = rec.get("account_id", account_id)
        created_at = rec.get("created_at")
        if created_at is None:
            results.append({**rec, "error": "created_at missing"}); continue
        created_at = _to_aware_ts(created_at)
        elapsed = SNAPSHOT_TIME - created_at
        severity = filters.get("severity") or _infer_severity(rec.get("subject", ""))
        sla_config = ACCOUNT_SLA.get(t_account_id)
        if not sla_config:
            results.append({**rec, "error": f"No SLA config for {t_account_id}",
                             "elapsed_str": _fmt_td(elapsed), "snapshot_time": SNAPSHOT_TIME.isoformat()})
            continue
        target = sla_config.get(severity, sla_config["P3"])
        results.append({**rec, "severity_inferred": severity,
                        "elapsed_str": _fmt_td(elapsed), "target_str": _fmt_td(target),
                        "breached": elapsed > target, "sla_source": sla_config["source"],
                        "sla_coverage": sla_config.get("coverage", ""),
                        "sla_note": sla_config.get("note", ""),
                        "snapshot_time": SNAPSHOT_TIME.isoformat()})
    return results


def _credit_calc(filters: dict, data_store: DataStore) -> list[dict]:
    order_id = filters.get("order_id")
    if not order_id:
        return [{"error": "order_id required for credit_calc"}]
    row = data_store.orders[data_store.orders["order_id"] == order_id]
    if row.empty:
        return [{"error": f"Order {order_id} not found"}]
    rec = _df_to_records(row)[0]
    account_id = rec.get("account_id")
    carrier_fault = rec.get("carrier_fault")
    customer_fault = rec.get("customer_fault")
    fee = rec.get("shipment_fee_inr", 0) or 0
    # Unknown fault status
    if carrier_fault is None or customer_fault is None:
        return [{**rec, "eligible": False,
                 "reason": "carrier_fault or customer_fault unconfirmed — verification required",
                 "snapshot_time": SNAPSHOT_TIME.isoformat()}]
    try:
        if pd.isna(carrier_fault) or pd.isna(customer_fault):
            return [{**rec, "eligible": False,
                     "reason": "carrier_fault or customer_fault unconfirmed — verification required",
                     "snapshot_time": SNAPSHOT_TIME.isoformat()}]
    except (TypeError, ValueError):
        pass
    if not bool(carrier_fault) or bool(customer_fault):
        return [{**rec, "eligible": False,
                 "reason": "Credit not eligible: carrier not at fault or customer at fault",
                 "snapshot_time": SNAPSHOT_TIME.isoformat()}]
    window_end = rec.get("pickup_window_end")
    if window_end is None:
        return [{"error": "pickup_window_end missing", **rec}]
    try:
        if pd.isna(window_end):
            return [{"error": "pickup_window_end missing", **rec}]
    except (TypeError, ValueError):
        pass
    window_end = _to_aware_ts(window_end)
    pickup_actual = rec.get("pickup_actual_at")
    valid_actual = pickup_actual is not None
    try:
        valid_actual = valid_actual and not pd.isna(pickup_actual)
    except (TypeError, ValueError):
        pass
    if valid_actual:
        delay = _to_aware_ts(pickup_actual) - window_end
    else:
        delay = SNAPSHOT_TIME - window_end
    if account_id == "ACCT-002":
        threshold = timedelta(hours=4)
        credit_source = "06_LumenWorks_Service_Agreement.pdf §3"
        if delay >= threshold:
            amount, eligible = 300, True
            reason = f"Delay {_fmt_td(delay)} ≥ LumenWorks 4h threshold. Fixed INR 300 per agreement §3."
        else:
            amount, eligible = 0, False
            reason = f"Delay {_fmt_td(delay)} < LumenWorks 4h threshold."
    elif account_id == "ACCT-001":
        threshold = timedelta(hours=2)
        credit_source = "03_Cancellation_and_Service_Credit_SOP_v4.pdf §2 + 05_Northstar_Logistics_Enterprise_Agreement.pdf §3"
        if delay >= threshold:
            amount = min(500, round(float(fee) * 0.10, 2))
            eligible = True
            reason = f"Delay {_fmt_td(delay)} ≥ 2h threshold. Credit: lower of INR 500 or 10% of INR {fee}. Cap INR 5,000/month per Northstar agreement §3."
        else:
            amount, eligible = 0, False
            reason = f"Delay {_fmt_td(delay)} < 2h SOP threshold."
    else:
        threshold = timedelta(hours=2)
        credit_source = "03_Cancellation_and_Service_Credit_SOP_v4.pdf §2"
        if delay >= threshold:
            amount = min(500, round(float(fee) * 0.10, 2))
            eligible = True
            reason = f"Delay {_fmt_td(delay)} ≥ 2h SOP threshold. Credit: lower of INR 500 or 10% of INR {fee}."
        else:
            amount, eligible = 0, False
            reason = f"Delay {_fmt_td(delay)} < 2h SOP threshold."
    return [{**rec, "eligible": eligible, "amount_inr": amount, "delay_str": _fmt_td(delay),
             "threshold_used": _fmt_td(threshold), "reason": reason, "credit_source": credit_source,
             "manager_approval_required": bool(eligible and amount > 1000),
             "snapshot_time": SNAPSHOT_TIME.isoformat()}]


def _proactive_sweep(data_store: DataStore) -> list[dict]:
    items: list[dict] = []
    open_tickets = data_store.tickets[data_store.tickets["status"] == "open"].copy()
    accounts_df = data_store.accounts

    def _acct_name(aid: str) -> str:
        r = accounts_df[accounts_df["account_id"] == aid]
        return str(r.iloc[0]["account_name"]) if not r.empty else aid

    for _, ticket in open_tickets.iterrows():
        t_id = ticket.get("ticket_id", "")
        account_id = ticket.get("account_id", "")
        subject = str(ticket.get("subject", ""))
        created_at = ticket.get("created_at")
        if created_at is None: continue
        try:
            if pd.isna(created_at): continue
        except (TypeError, ValueError): pass
        created_at = _to_aware_ts(created_at)
        severity = _infer_severity(subject)
        sla_config = ACCOUNT_SLA.get(account_id, ACCOUNT_SLA["ACCT-003"])
        target = sla_config.get(severity, sla_config["P3"])
        elapsed = SNAPSHOT_TIME - created_at
        if elapsed > target:
            items.append({"category": "SLA Breach", "ticket_ids": [t_id], "account_id": account_id,
                          "account_name": _acct_name(account_id),
                          "recommended_action": f"Escalate — {severity} SLA breached ({_fmt_td(elapsed)} elapsed, target {_fmt_td(target)})",
                          "suggested_query": f"Tell me about {t_id} and whether I should escalate"})
        elif elapsed > target * 0.8:
            items.append({"category": "Approaching SLA", "ticket_ids": [t_id], "account_id": account_id,
                          "account_name": _acct_name(account_id),
                          "recommended_action": f"Review urgently — {_fmt_td(target - elapsed)} remaining before {severity} breach",
                          "suggested_query": f"What's the status and urgency of {t_id}?"})
        # KI detection
        subject_lower = subject.lower()
        for ki in KI_PATTERNS:
            if any(kw in subject_lower for kw in ki["keywords"]):
                items.append({"category": "KI-Linked", "ticket_ids": [t_id], "account_id": account_id,
                              "account_name": _acct_name(account_id),
                              "recommended_action": f"Linked to {ki['ki_id']}: {ki['description']}",
                              "suggested_query": f"Is {t_id} related to {ki['ki_id']}? What should I tell the customer?"})
                break

    # ── Account clustering: 2+ open tickets in 7-day window ──────────────────
    cutoff = SNAPSHOT_TIME - timedelta(days=7)
    try:
        recent = open_tickets[open_tickets["created_at"] >= cutoff]
    except Exception:
        recent = open_tickets
    groups = recent.groupby("account_id")["ticket_id"].apply(list)
    for acct_id, tkt_ids in groups.items():
        if len(tkt_ids) >= 2:
            items.append({
                "category": "Account Cluster",
                "ticket_ids": list(tkt_ids),
                "account_id": acct_id,
                "account_name": _acct_name(acct_id),
                "recommended_action": f"{len(tkt_ids)} open tickets from this account in 7 days",
                "suggested_query": f"What open tickets does {_acct_name(acct_id)} have and is there a pattern?",
            })

    # ── Semantic similarity clustering across all open tickets ────────────────
    # Groups tickets by subject similarity (TF-IDF cosine ≥ 0.35) so agents
    # can spot systemic issues that keyword matching alone misses.
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        subjects   = [str(t.get("subject", "")) for _, t in open_tickets.iterrows()]
        ticket_ids = [t.get("ticket_id", "") for _, t in open_tickets.iterrows()]
        acct_ids   = [t.get("account_id", "") for _, t in open_tickets.iterrows()]

        if len(subjects) >= 2:
            vec = TfidfVectorizer(stop_words="english", min_df=1)
            tfidf = vec.fit_transform(subjects)
            sim = cosine_similarity(tfidf)

            CLUSTER_THRESHOLD = 0.35
            seen_pairs: set = set()
            for i in range(len(ticket_ids)):
                for j in range(i + 1, len(ticket_ids)):
                    pair = tuple(sorted([ticket_ids[i], ticket_ids[j]]))
                    if pair in seen_pairs:
                        continue
                    if (sim[i, j] >= CLUSTER_THRESHOLD
                            and acct_ids[i] != acct_ids[j]):  # cross-account semantic match
                        seen_pairs.add(pair)
                        items.append({
                            "category": "Semantic Cluster",
                            "ticket_ids": [ticket_ids[i], ticket_ids[j]],
                            "account_id": f"{acct_ids[i]}/{acct_ids[j]}",
                            "account_name": f"{_acct_name(acct_ids[i])} + {_acct_name(acct_ids[j])}",
                            "recommended_action": (
                                f"Semantically similar tickets from different accounts "
                                f"(similarity={sim[i,j]:.2f}) — possible systemic issue"
                            ),
                            "suggested_query": (
                                f"Are {ticket_ids[i]} and {ticket_ids[j]} related to the same root cause?"
                            ),
                        })
    except ImportError:
        pass  # sklearn not available — account clusters above are sufficient

    return items


def _infer_severity(subject: str) -> str:
    lower = subject.lower()
    for kw in ["outage", "failing", "500", "api key", "credential", "security", "all shipment"]:
        if kw in lower: return "P1"
    for kw in ["fail", "error", "degraded", "slow", "intermittent", "bulk upload", "csv"]:
        if kw in lower: return "P2"
    return "P3"


def _to_aware_ts(val: Any) -> pd.Timestamp:
    from zoneinfo import ZoneInfo
    _IST = ZoneInfo("Asia/Kolkata")
    if isinstance(val, str):
        ts = pd.Timestamp(val)
    elif isinstance(val, pd.Timestamp):
        ts = val
    else:
        ts = pd.Timestamp(val)
    if ts.tzinfo is None:
        ts = ts.tz_localize(_IST)
    return ts


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    records = df.to_dict(orient="records")
    clean = []
    for rec in records:
        cleaned = {}
        for k, v in rec.items():
            if isinstance(v, pd.Timestamp):
                cleaned[k] = v.isoformat()
            elif isinstance(v, float) and pd.isna(v):
                cleaned[k] = None
            elif hasattr(v, "item"):
                cleaned[k] = v.item()
            else:
                cleaned[k] = v
        clean.append(cleaned)
    return clean


def _fmt_td(td: timedelta) -> str:
    total = int(td.total_seconds())
    if total < 0: return "0m"
    d = total // 86400; h = (total % 86400) // 3600; m = (total % 3600) // 60
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m or not parts: parts.append(f"{m}m")
    return " ".join(parts)
