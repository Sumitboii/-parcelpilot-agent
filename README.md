# 🚁 ParcelPilot — Production AI Support Copilot

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-RAG-ff6600?style=for-the-badge)](https://www.trychroma.com)
[![Groq LLM](https://img.shields.io/badge/Groq-GPT--OSS--20B%2F120B-f05032?style=for-the-badge)](https://groq.com)
[![Railway Deployed](https://img.shields.io/badge/Railway-Live_Demo-0B0D0E?style=for-the-badge&logo=railway)](https://parcelpilot-agent-production.up.railway.app/showcase)
[![Test Suite](https://img.shields.io/badge/pytest-60%2F60_Passing-brightgreen?style=for-the-badge&logo=pytest)](https://docs.pytest.org)

---

## 🌐 **Live Interactive Demo**

**Hosted Link:** [parcelpilot-agent-production.up.railway.app/showcase](https://parcelpilot-agent-production.up.railway.app/showcase)

> **Role Switching Support:** Seamlessly test as **Support Agent** (sanitised data layer) or **CSM / Escalation Manager** (full visibility into SLA targets, internal notes, and tier contracts).

---

## 📌 Executive Overview

**ParcelPilot Support Copilot** is a production-grade, multi-agent RAG system built for internal operations teams handling complex B2B logistics queries. 

Unlike standard conversational wrappers, ParcelPilot implements **deterministic source hierarchy enforcement**, **real-time SSE streaming**, **proactive issue clustering**, **semantic conflict detection**, and an **audited confirmation gate** for state-changing operations.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ParcelPilot Architecture                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────┐          ┌────────────────────────────────┐   │
│   │   Product Showcase UI   │ ◄──────► │  FastAPI Server (SSE Stream)   │   │
│   │   (React / Compass JS)  │          └──────────────┬─────────────────┘   │
│   └─────────────────────────┘                         │                     │
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
│     │ (ChromaDB Vector)│    │ (Pandas / XLSX)  │    │(Audit Log JSONL) │    │
│     └──────────────────┘    └──────────────────┘    └──────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔑 Core Capabilities & 10/10 Specs

### 1. Locked Source-Authority Hierarchy
The system strictly resolves policy conflicts per `01_Support_Policy_v3_CURRENT.pdf §1`:
1. **Signed Customer Agreements** *(Highest — overrides everything for that account)*
2. **Current Policy v3** — `01_Support_Policy_v3_CURRENT.pdf`
3. **SOPs & Guides** — Cancellation & Service Credit SOP v4 / Product Operations Guide
4. **Historical Tickets** — Contextual reference only *(known errors overridden)*

> 🔒 **Deprecated Policy Filtering:** `02_Support_Policy_v2_DEPRECATED.pdf` is filtered at ingest time and **never** returned or indexed for reasoning.

### 2. Proactive Issue Detection (Zero-Query Sidebar)
On UI load, the backend automatically performs a proactive sweep:
- 🚨 **SLA Breach Monitoring:** Identifies P1/P2 tickets exceeding response windows (e.g. TKT-501, TKT-505).
- 🐛 **Known Issue (KI) Linking:** Matches ticket symptoms to Known Issues (KI-208, KI-211).
- 👥 **Account Cluster & Semantic Clustering:** Detects accounts with 2+ open tickets in 7 days, plus TF-IDF cross-account semantic pattern matching.

### 3. State-Changing Confirmation Gate
Operations that modify system state (e.g., ticket escalations, refund approvals) do **not** execute automatically. The agent generates a structured **Pending Confirmation Card** requiring explicit staff approval before writing to the audit log (`data/escalations.jsonl`).

### 4. Role-Based Data Sanitisation
- **Support Agent:** Sensitive fields (`premium_support`, internal notes, contract tier specifics) are stripped at the data provider layer.
- **CSM / Escalation Manager:** Access to full un-redacted account data, customized SLA calculation, and priority queue management.

### 5. Multi-Step Reasoning & Citation
Every answer explicitly cites governing documents and structured records, providing step-by-step reasoning for SLA calculations, cancellation fees, and service credits.

---

## 🎯 Verification Benchmark Matrix (All 60 Tests Passing)

| Benchmark Scenario | Core Challenge | Policy Hierarchy & System Resolution | Status |
| :--- | :--- | :--- | :---: |
| **Northstar ORD-1001 Cancellation** | ORD-1001 placed 2h ago. SOP says 30m limit; wrong historical ticket (TKT-450) charged fee. | **No Fee:** Signed Agreement §2 (no cancellation fee anytime before dispatch) overrides SOP & wrong historical record. | ✅ PASSED |
| **LumenWorks 4,200-Row CSV Upload** | Upload failing at 4,200 rows. Policy says limit is 5,000. Wrong historical ticket (TKT-451) claims 3,000 limit. | **KI-208 Workaround:** Global product limit is 5,000, but KI-208 bug causes failures above ~3,000 rows. Recommends split batch. | ✅ PASSED |
| **TKT-504 SwiftShip Status Delay** | Ticket shows `BOOKED` but driver physically picked up package. | **KI-211 Webhook Delay:** Identifies 20-minute SwiftShip webhook latency; driver pickup confirmed valid. | ✅ PASSED |
| **LumenWorks ORD-2002 Credit** | 4.5h delay on ORD-2002. SOP mandates 2h threshold / ₹500 credit. | **INR 300 Fixed Credit:** Signed Agreement §4 overrides SOP — requires 4h threshold and caps credit at INR 300. | ✅ PASSED |
| **Axis Labs TKT-505 SLA Breach** | P1 ticket open for 2.5h. Standard SLA is 1h; Northstar SLA is 15m. | **30m Enterprise SLA:** Axis Labs agreement specifies 30m target. SLA breached by 2h; flags immediate escalation. | ✅ PASSED |
| **ACCT-004 Default Enterprise Policy** | Account has no custom agreement attached. | **Standard Support Policy v3:** Falls back cleanly to general policy without borrowing terms from other accounts. | ✅ PASSED |

---

## 🛠️ Stack & Technology Decisions

- **LLM Engine:** Groq `openai/gpt-oss-20b` (Primary) & `openai/gpt-oss-120b` (Fallback) with key rotation pool.
- **RAG & Vector Engine:** In-memory ChromaDB + `sentence-transformers/all-MiniLM-L6-v2`.
- **Structured Data:** High-performance `pandas` DataFrames loading multi-tab XLSX files.
- **Backend Service:** FastAPI with Server-Sent Events (`sse-starlette`) for real-time token streaming.
- **Frontend App:** Single-file standalone HTML showcase (`PRODUCT_SHOWCASE.html`) + Vite React 18 frontend.
- **Containerization & Hosting:** Dockerized deployment hosted on Railway.

---

## ⚡ Quick Start & Running Locally

### Prerequisites
- Python 3.11+
- Node.js 20+ (optional, for React frontend)
- Groq API Key ([Get free key](https://console.groq.com))

### Setup & Launch

```bash
# 1. Clone the repository
git clone https://github.com/Sumitboii/-parcelpilot-agent.git
cd -parcelpilot-agent

# 2. Configure Environment
cp .env.example .env
# Edit .env and insert your GROQ_API_KEY

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Start Backend Server
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open your browser to:
- 📱 **Interactive Showcase UI:** [`http://localhost:8000/showcase`](http://localhost:8000/showcase)
- ⚙️ **API Documentation:** [`http://localhost:8000/docs`](http://localhost:8000/docs)
- 🏥 **Healthcheck Endpoint:** [`http://localhost:8000/health`](http://localhost:8000/health)

---

## 🧪 Running the Test Suite

```bash
# Run pytest across all 60 unit, integration, and scenario tests
python -m pytest
```

Output:
```text
collected 60 items

tests/test_data_loader.py .........                                      [ 15%]
tests/test_data_lookup.py ................                               [ 41%]
tests/test_document_search.py ......                                     [ 51%]
tests/test_escalate_and_gate.py .............                            [ 73%]
tests/test_evaluation_matrix.py ...........                              [ 91%]
tests/test_vector_store.py .....                                         [100%]

================== 60 passed in 76.88s ==================
```

---

## 🐳 Docker Deployment

Build and run using Docker:

```bash
# Build the Docker image
docker build -t parcelpilot-agent .

# Run the container
docker run -d -p 8000:8000 --env-file .env --name parcelpilot parcelpilot-agent
```

---

## 📝 Video Demo Script / Evaluation Walkthrough

If recorded for demonstration or submission evaluation, follow this 2-minute flow:

1. **Proactive Sidebar (0:00 - 0:30):** Point out zero-query load items — P1 SLA breaches (TKT-501, TKT-505), KI links (KI-208, KI-211), and Account Clusters.
2. **Policy Hierarchy Override (0:30 - 1:10):** Ask: *"Can Northstar cancel ORD-1001 without a fee?"* Highlight how the agent ignores SOP 30-min limits and wrong historical ticket TKT-450, correctly citing Northstar Agreement §2.
3. **Known Issue & Workaround (1:10 - 1:35):** Ask about LumenWorks CSV failure. Observe the agent identifying KI-208 and providing the 3,000-row batch splitting workaround.
4. **Confirmation Gate (1:35 - 2:00):** Request escalation for TKT-505. Show the inline confirmation card requiring explicit human approval before committing the action.

---

## ⚠️ Known Deployment Notes

- **`data/escalations.jsonl` Ephemerality:** On Railway, the local container filesystem resets on every redeploy. Escalation confirmation audit logs reset accordingly. In production, this logger plugs into PostgreSQL or Cloud Logging via `backend/tools/escalate.py`.

---

## 📄 License & Attribution

Built for the ParcelPilot AI Agent Assessment. All test datasets and policy source documents are property of ParcelPilot Inc.
