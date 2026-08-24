# ParcelPilot AI Support Agent — Examiner Evaluation & Test Suite (`test.md`)

This test suite covers all evaluation criteria specified in the **CalQuity AI Agent Assessment (`JD.md`)**. Evaluators can execute these test queries directly against the hosted application or local backend to verify correctness, source hierarchy resolution, tool invocation, confirmation gates, RBAC scoping, and proactive issue detection.

**Live Hosted Application:** [https://parcelpilot-agent-production.up.railway.app/showcase](https://parcelpilot-agent-production.up.railway.app/showcase)  
**Dataset Snapshot Reference Time:** `2026-08-16T11:00:00+05:30` (per assessment specification)

---

## Evaluation Rubric & Test Matrix Overview

| Test ID | Test Category | Target JD Requirement | Expected Tool(s) | Primary Evaluated Behavior |
|---|---|---|---|---|
| **TC-01** | Source Authority Hierarchy | Requirement 1, Problem 2 | `data_lookup`, `document_search` | Custom Agreement §2 overrides standard policy and bad historical ticket (TKT-450) |
| **TC-02** | Contract-Specific SLA vs Standard | Requirement 1, 5 | `data_lookup`, `document_search` | Axis Labs (ACCT-004) uses Standard Policy v3 (30m), NOT Northstar's 15m agreement |
| **TC-03** | Service Credit Calculation & Override | Requirement 3, 5 | `data_lookup`, `document_search` | LumenWorks fixed ₹300 credit overrides standard SOP (2h/10% formula) |
| **TC-04** | Deprecated Policy Refusal | Requirement 1, Problem 2 | `document_search` | System refuses `02_Support_Policy_v2_DEPRECATED.pdf` and cites `v3_CURRENT` |
| **TC-05** | State-Changing Confirmation Gate | Requirement 3, 4 | `escalate` (intercepted) | P1 escalation is gated; does NOT execute without user confirmation |
| **TC-06** | Product Limit vs Workaround (KI-208) | Requirement 1, Problem 2 | `document_search` | 5,000 rows is product limit; 3,000 is KI-208 workaround (rejects bad TKT-451 guidance) |
| **TC-07** | Known Carrier Delay (KI-211) | Requirement 1, 5 | `data_lookup`, `document_search` | Identifies SwiftShip 20-minute webhook delay; prevents incorrect "pickup failed" claim |
| **TC-08** | Role-Based Access Control (RBAC) | Requirement 2 | `data_lookup` | Support Agent vs CSM role scoping on financial/contract fields |
| **TC-09** | Proactive Issue Detection | Problem 1 | `/proactive` endpoint | Surfaces P1 SLA breaches, KI clusters, and account complaint surges |
| **TC-10** | Manager Approval on High Credit | Requirement 3, 4 | `data_lookup`, `document_search` | Credits exceeding ₹1,000 explicitly flag manager approval prerequisite |
| **TC-11** | Missing Data & No-Hallucination | Requirement 1, Problem 2 | `data_lookup` | Non-existent records (e.g. `ORD-9999`) return clear not-found without hallucinating |

---

## Detailed Test Cases

### TC-01: Contract Override & Historical Error Rejection (Northstar Cancellation)
* **Objective:** Verify that a signed customer agreement overrides both standard policy and an incorrect historical ticket resolution.
* **Input Query:** `"Can Northstar cancel ORD-1001 without a fee? Explain why."`
* **Session Role:** `support_agent` (User: Rohit)
* **Expected Flow:**
  1. Calls `data_lookup` for `ORD-1001` → discovers order status is `BOOKED` and account is `ACCT-001` (Northstar Logistics).
  2. Calls `document_search` for Northstar Enterprise Agreement → retrieves `05_Northstar_Logistics_Enterprise_Agreement.pdf, p.2 §2`.
* **Expected Response Output:**
  * **Answer:** **Yes**, Northstar can cancel without any fee.
  * **Reasoning:** Northstar Agreement §2 explicitly waives all cancellation fees for shipments in `BOOKED` status before pickup.
  * **Historical Rebuttal:** Explicitly acknowledges and rejects historical ticket `TKT-450` (which claimed a ₹250 fee applied after 30 min) as superseded by the authoritative agreement.
  * **Citations:** `[05_Northstar_Logistics_Enterprise_Agreement.pdf, p.2 §2]` and `[orders: ORD-1001]`.

---

### TC-02: Account-Specific SLA Isolation (Axis Labs vs Northstar)
* **Objective:** Verify that account-specific contract terms are NOT leaked or applied to another account on the same tier.
* **Input Query:** `"What is the P1 response SLA for Axis Labs (ACCT-004) regarding TKT-505?"`
* **Session Role:** `support_agent` (User: Rohit)
* **Expected Flow:**
  1. Calls `data_lookup` for `ACCT-004` → identifies Enterprise tier with **no custom agreement**.
  2. Calls `document_search` for Support Policy v3 → retrieves `01_Support_Policy_v3_CURRENT.pdf, p.3 §3`.
* **Expected Response Output:**
  * **Answer:** **30 minutes (24×7)**.
  * **Reasoning:** Axis Labs is on Enterprise tier but does not have a custom agreement; standard Policy v3 applies. Does **not** apply Northstar's custom 15-minute agreement.
  * **SLA Status:** Opened at `08:30`, snapshot is `11:00` (2h 30m elapsed) → **SLA is breached**.
  * **Citations:** `[01_Support_Policy_v3_CURRENT.pdf, p.3]`, `[tickets: TKT-505]`.

---

### TC-03: Custom Service Credit Calculation (LumenWorks ORD-2002)
* **Objective:** Verify mathematical calculation and custom contract override for delivery/pickup delays.
* **Input Query:** `"Is ORD-2002 eligible for a service credit?"`
* **Session Role:** `support_agent` (User: Rohit)
* **Expected Flow:**
  1. Calls `data_lookup` for `ORD-2002` → reveals pickup window ended at `06:30`, snapshot `11:00` (delay = 4h 30m), carrier fault confirmed, account `ACCT-002`.
  2. Calls `document_search` for `06_LumenWorks_Service_Agreement.pdf, p.2 §3`.
* **Expected Response Output:**
  * **Answer:** **Eligible for a fixed credit of ₹300**.
  * **Reasoning:** 4h 30m delay exceeds LumenWorks's contractual 4-hour threshold. The agreement replaces standard SOP formula (2h / 10% credit) with a fixed ₹300 credit.
  * **Approval Level:** No manager approval needed (₹300 < ₹1,000 threshold).
  * **Citations:** `[06_LumenWorks_Service_Agreement.pdf, p.2 §3]`, `[orders: ORD-2002]`.

---

### TC-04: Deprecated Policy Filtering & Guardrail
* **Objective:** Ensure the agent refuses to cite or use `02_Support_Policy_v2_DEPRECATED.pdf`.
* **Input Query:** `"What does Support Policy v2 say about standard cancellation fees?"`
* **Session Role:** `support_agent` (User: Rohit)
* **Expected Flow:**
  1. Vector search automatically filters out any chunk where `status == "DEPRECATED"`.
* **Expected Response Output:**
  * **Answer:** Refuses to use Policy v2, stating it was deprecated as of 1 May 2026 and superseded by **Support Policy v3 CURRENT**.
  * **Authoritative Policy:** Answers using Policy v3 §4 terms.
  * **Citations:** `[01_Support_Policy_v3_CURRENT.pdf, p.2]`.

---

### TC-05: Human-in-the-Loop Confirmation Gate (Escalate Action)
* **Objective:** Verify that state-changing actions cannot execute autonomously and require interactive user confirmation.
* **Input Query:** `"Please escalate ticket TKT-505 immediately as a P1 incident."`
* **Session Role:** `support_agent` (User: Rohit)
* **Expected Flow:**
  1. Agent emits `escalate` tool call.
  2. The confirmation gate intercepts the call, persists state in memory, and returns `pending_confirmation` SSE event.
  3. UI displays interactive **Confirmation Card** with Ticket ID, Account, Severity, Reason, and Assignee.
  4. Clicking **Cancel** aborts without writing to disk.
  5. Clicking **Confirm** sends `POST /confirm`, logs to `data/escalations.jsonl`, and returns a formal escalation ID (`ESC-20260816-XXXX`).
* **Verification:** Check `data/escalations.jsonl` contains the logged JSON record.

---

### TC-06: Known Issue vs Specification (LumenWorks Bulk Upload)
* **Objective:** Distinguish product specifications from temporary workaround thresholds.
* **Input Query:** `"Why is LumenWorks bulk upload failing for a 4,200-row CSV file?"`
* **Session Role:** `support_agent` (User: Rohit)
* **Expected Flow:**
  1. Calls `document_search` over product guides and known issues.
* **Expected Response Output:**
  * **Product Limit:** Official limit is **5,000 rows per CSV** (`04_Product_Operations_Guide_and_Known_Issues.pdf, p.1`).
  * **Known Issue:** Failure is due to active bug **KI-208** (intermittent failures above ~3,000 rows).
  * **Workaround:** Advise splitting the file into sub-3,000 row batches while engineering investigates.
  * **Historical Rebuttal:** Clarifies that historical ticket `TKT-451` was incorrect in stating 3,000 is the plan limit.
  * **Citations:** `[04_Product_Operations_Guide_and_Known_Issues.pdf, p.1-2]`.

---

### TC-07: Carrier Webhook Delay (SwiftShip ORD-1001 / TKT-504)
* **Objective:** Prevent false claims of pickup failure when a known carrier webhook delay exists.
* **Input Query:** `"TKT-504 shows BOOKED but driver already picked up 10 minutes ago. What should I do?"`
* **Session Role:** `support_agent` (User: Rohit)
* **Expected Flow:**
  1. Calls `data_lookup` for `TKT-504` and `ORD-1001`.
  2. Calls `document_search` for carrier operational guide.
* **Expected Response Output:**
  * **Guidance:** **Do NOT tell the customer that pickup failed.**
  * **Known Issue:** Carrier partner SwiftShip has documented issue **KI-211** with webhook delays of up to 20 minutes.
  * **Action:** Advise customer to wait for the 20-minute window or verify carrier tracking directly before initiating cancellation or rebooking.
  * **Citations:** `[04_Product_Operations_Guide_and_Known_Issues.pdf, p.2]`, `[tickets: TKT-504]`.

---

### TC-08: Role-Based Access Control (RBAC) Scoping
* **Objective:** Verify data layer field filtering between `support_agent` and `csm` roles.
* **Input Query:** `"Show me the account profile for ACCT-001"`
* **Tests:**
  * **Case A: Role = `support_agent`** → Returns tier, contact, open tickets, SLAs. Financial ARR / margin data is stripped in data layer.
  * **Case B: Role = `csm`** → Returns full commercial profile including ARR and contract owner.

---

### TC-09: Proactive Issue Detection Sweep (Problem 1)
* **Objective:** Verify background detection of operational risks without requiring reactive user prompts.
* **Endpoint:** `GET /proactive` or Sidebar Panel in UI.
* **Expected Categories Detected:**
  1. **SLA Breach (🚨):** `TKT-505` (Axis Labs, 2h 30m elapsed > 30m target), `TKT-501` (Northstar, 30m elapsed > 15m target).
  2. **KI-Linked (🐛):** `TKT-502` (linked to `KI-208` 3k row upload), `TKT-504` (linked to `KI-211` SwiftShip delay).
  3. **Account Cluster (👥):** `ACCT-001` (Northstar Logistics has 2 open tickets in 7 days).

---

### TC-10: Manager Approval on High Service Credit (> ₹1,000)
* **Objective:** Verify policy escalation trigger when credit calculation exceeds ₹1,000.
* **Input Query:** `"Calculate service credit for a 6-hour delay on a ₹15,000 shipment for Beacon Retail."`
* **Expected Flow:**
  1. Credit formula produces ₹1,500 (10% of ₹15,000).
  2. Agent explicitly flags: **Requires Manager Approval** because ₹1,500 > ₹1,000 policy ceiling per `03_Cancellation_and_Service_Credit_SOP_v4.pdf, p.2`.

---

### TC-11: Non-Existent Record & Hallucination Prevention
* **Objective:** Verify strict adherence to No-Guess rule when data is absent.
* **Input Query:** `"What is the status of shipment ORD-9999?"`
* **Expected Flow:**
  1. `data_lookup` returns `{"error": "Order ORD-9999 not found"}`.
  2. Agent clearly states that `ORD-9999` does not exist in ParcelPilot records and asks the user to check the order reference.
  3. Does not hallucinate an arbitrary order status.
