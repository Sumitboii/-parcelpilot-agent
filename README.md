# 🚁 ParcelPilot — Production AI Support Copilot

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Render Deployed](https://img.shields.io/badge/Render-Live_Demo-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://parcelpilot-agent-05e4.onrender.com)
[![Test Suite](https://img.shields.io/badge/pytest-66%2F66_Passing-brightgreen?style=for-the-badge&logo=pytest)](https://docs.pytest.org)

---

## 🌐 **Live Interactive Demo**

* **Production Live URL (Render):** [https://parcelpilot-agent-05e4.onrender.com](https://parcelpilot-agent-05e4.onrender.com)

> **Role Switching Support:** Seamlessly test as **Support Agent** (sanitised data layer) or **CSM / Escalation Manager** (full visibility into SLA targets, internal notes, and tier contracts).

---

## 📌 Executive Overview

**ParcelPilot Support Copilot** is a production-grade, multi-agent RAG system built for internal operations teams handling complex B2B logistics queries. 

Unlike standard conversational wrappers, ParcelPilot implements **deterministic source hierarchy enforcement**, **real-time SSE streaming**, **multi-key health step function**, **proactive issue clustering**, **semantic conflict detection**, and an **audited confirmation gate** for state-changing operations.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ParcelPilot Architecture                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────┐          ┌────────────────────────────────┐   │
│   │   Product Showcase UI   │ ◄──────► │  FastAPI Server (SSE Stream)   │   │
│   │   (React / DOM Events)  │          └──────────────┬─────────────────┘   │
│   └─────────────────────────┘                         │                     │
│                                                       ▼                     │
│                                        ┌────────────────────────────────┐   │
│                                        │  Groq Multi-Key Pool Manager   │   │
│                                        │ (Zero-Latency LRU + 429 Retry) │   │
│                                        └──────────────┬─────────────────┘   │
│                                                       │                     │
│                                                       ▼                     │
│                                        ┌────────────────────────────────┐   │
│                                        │ Hand-Rolled Agent Tool-Router │   │
│                                        │  (Groq GPT-OSS 20B/120B Pool)  │   │
│                                        └──────────────┬─────────────────┘   │
│                                                       │                     │
│               ┌───────────────────────┬───────────────┴───────────────┐     │
│               ▼                       ▼                               ▼     │
│     ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    │
│     │ Document Search  │    │   Data Lookup    │    │ Escalation Gate  │    │
│     │(In-Memory Vector)│    │ (Pandas / XLSX)  │    │(Audit Log JSONL) │    │
│     └──────────────────┘    └──────────────────┘    └──────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔑 Core Capabilities

### 1. Multi-Key Health Step Function & Zero-Latency Routing
- Automatically discovers keys from `GROQ_API_KEYS` and `GROQ_API_KEY_1..5`.
- **Zero-Latency In-Memory LRU**: Dispatches requests instantly using least-recently-used healthy keys without blocking pre-flight checks.
- **429 & 413 Failover Step Function**: Seamlessly retries on the next healthy pool key if rate limits or token bounds are hit.
- **Background Health Monitor**: Periodically verifies key status every 30s in an asynchronous background worker.

### 2. Locked Source-Authority Hierarchy
The system strictly resolves policy conflicts per `01_Support_Policy_v3_CURRENT.pdf §1`:
1. **Signed Customer Agreements** *(Highest — overrides everything for that account)*
2. **Current Policy v3** — `01_Support_Policy_v3_CURRENT.pdf`
3. **SOPs & Guides** — Cancellation & Service Credit SOP v4 / Product Operations Guide
4. **Historical Tickets** — Contextual reference only *(known errors overridden)*

> 🔒 **Deprecated Policy Filtering:** `02_Support_Policy_v2_DEPRECATED.pdf` is filtered at ingest time and **never** returned or indexed for reasoning.

### 3. Proactive Issue Detection (Zero-Query Sidebar)
On UI load, the backend automatically performs a proactive sweep:
- 🚨 **SLA Breach Monitoring:** Identifies P1/P2 tickets exceeding response windows (e.g. TKT-501, TKT-505).
- 🐛 **Known Issue (KI) Linking:** Matches ticket symptoms to Known Issues (KI-208, KI-211).
- 👥 **Account Cluster & Semantic Clustering:** Detects accounts with 2+ open tickets in 7 days, plus TF-IDF cross-account semantic pattern matching.

### 4. State-Changing Confirmation Gate
Operations that modify system state (e.g., ticket escalations, refund approvals) do **not** execute automatically. The agent generates a structured **Pending Confirmation Card** requiring explicit staff approval before writing to the audit log (`data/escalations.jsonl`).

### 5. Role-Based Data Sanitisation
- **Support Agent:** Sensitive fields (`premium_support`, internal notes, contract tier specifics) are stripped at the data provider layer.
- **CSM / Escalation Manager:** Access to full un-redacted account data, customized SLA calculation, and priority queue management.

---

## 🎯 Verification Benchmark Matrix (All 66 Tests Passing)

| Benchmark Scenario | Core Challenge | Policy Hierarchy & System Resolution | Status |
| :--- | :--- | :--- | :---: |
| **Northstar ORD-1001 Cancellation** | ORD-1001 placed 2h ago. SOP says 30m limit; wrong historical ticket (TKT-450) charged fee. | **No Fee:** Signed Agreement §2 (no cancellation fee anytime before dispatch) overrides SOP & wrong historical record. | ✅ PASSED |
| **LumenWorks 4,200-Row CSV Upload** | Upload failing at 4,200 rows. Policy says limit is 5,000. Wrong historical ticket (TKT-451) claims 3,000 limit. | **KI-208 Workaround:** Global product limit is 5,000, but KI-208 bug causes failures above ~3,000 rows. Recommends split batch. | ✅ PASSED |
| **TKT-504 SwiftShip Status Delay** | Ticket shows `BOOKED` but driver physically picked up package. | **KI-211 Webhook Delay:** Identifies 20-minute SwiftShip webhook latency; driver pickup confirmed valid. | ✅ PASSED |
| **LumenWorks ORD-2002 Credit** | 4.5h delay on ORD-2002. SOP mandates 2h threshold / ₹500 credit. | **INR 300 Fixed Credit:** Signed Agreement §4 overrides SOP — requires 4h threshold and caps credit at INR 300. | ✅ PASSED |
| **Axis Labs TKT-505 SLA Breach** | P1 ticket open for 2.5h. Standard SLA is 1h; Northstar SLA is 15m. | **30m Enterprise SLA:** Axis Labs agreement specifies 30m target. SLA breached by 2h; flags immediate escalation. | ✅ PASSED |
| **ACCT-004 Default Enterprise Policy** | Account has no custom agreement attached. | **Standard Support Policy v3:** Falls back cleanly to general policy without borrowing terms from other accounts. | ✅ PASSED |
| **Groq Multi-Key Pool Step Function** | Key rotation, health probes, LRU selection, cooldown recovery. | **Zero-Latency Rotation:** Smooth failover and background recovery tested across concurrent requests. | ✅ PASSED |

---

## 🛠️ Stack & Technology Decisions

- **LLM Engine:** Groq `openai/gpt-oss-20b` (Primary) & `openai/gpt-oss-120b` (Fallback) with multi-key pool.
- **RAG & Vector Engine:** In-memory lightweight vector store (< 40MB RAM) with authority ranking.
- **Structured Data:** High-performance `pandas` DataFrames loading multi-tab XLSX files.
- **Backend Service:** FastAPI with Server-Sent Events (`sse-starlette`) for real-time token streaming.
- **Frontend App:** Standalone interactive HTML showcase (`PRODUCT_SHOWCASE.html`) with DOM event listeners.
- **Deployment:** Render (`render.yaml` Blueprint / Docker) + Railway.

---

## ⚡ Quick Start & Running Locally

### Prerequisites
- Python 3.11+
- Groq API Key ([Get free key](https://console.groq.com))

### Setup & Launch

```bash
# 1. Clone the repository
git clone https://github.com/Sumitboii/-parcelpilot-agent.git
cd -parcelpilot-agent

# 2. Configure Environment
cp .env.example .env
# Edit .env and insert your GROQ_API_KEYS or GROQ_API_KEY

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Start Server
python start.py
```

Open your browser to:
- 📱 **Interactive Showcase UI:** [`http://localhost:8000`](http://localhost:8000)
- ⚙️ **API Documentation:** [`http://localhost:8000/docs`](http://localhost:8000/docs)
- 🏥 **Healthcheck Endpoint:** [`http://localhost:8000/health`](http://localhost:8000/health)

---

## 🧪 Running the Test Suite

```bash
# Run pytest across all 66 unit, integration, and scenario tests
python -m pytest
```

Output:
```text
============================== test session starts ==============================
collected 66 items

tests/test_data_loader.py .........                                      [ 13%]
tests/test_data_lookup.py ................                               [ 37%]
tests/test_document_search.py ......                                     [ 46%]
tests/test_escalate_and_gate.py .............                            [ 66%]
tests/test_evaluation_matrix.py ...........                              [ 83%]
tests/test_key_manager.py ......                                         [ 92%]
tests/test_vector_store.py .....                                         [100%]

======================= 66 passed, 1 warning in 45.35s =======================
```

---

## 📄 License & Attribution

Built for the ParcelPilot AI Agent Assessment. All test datasets and policy source documents are property of ParcelPilot Inc.
