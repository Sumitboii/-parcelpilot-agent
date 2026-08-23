# ParcelPilot Internal Support Agent

An AI-powered internal chatbot for ParcelPilot's support and operations team. Built for the ParcelPilot AI Agent assessment.

**Live demo:** [parcelpilot-agent-production.up.railway.app](https://parcelpilot-agent-production.up.railway.app/showcase)

---

## What it does

Internal staff ask questions in plain language about customer orders, accounts, tickets, and policies. The agent reasons across 6 source documents and a structured dataset, cites every factual claim, and surfaces the correct answer per a locked source-authority hierarchy — even when historical records are wrong.

Key capabilities:

- **Multi-step reasoning** — chains document search, data lookup, and credit/SLA calculations in a single query
- **Source authority enforcement** — signed customer agreements override general policies; deprecated docs are filtered at ingest and never surfaced
- **Proactive issue detection** — sidebar sweeps all open tickets for SLA breaches, KI-linked patterns, and account clusters without requiring a query
- **Escalation with confirmation** — state-changing actions always require explicit staff approval via an inline confirmation card
- **Role-based access** — CSM-only fields (`premium_support`, `notes`) are stripped at the data layer for Support Agent sessions

---

## Stack

| Layer | Choice |
|---|---|
| LLM | Groq `openai/gpt-oss-120b` (free tier) |
| Agent | Hand-rolled Python tool-router — no LangChain |
| RAG | ChromaDB in-memory + `all-MiniLM-L6-v2` (local) |
| Structured data | pandas DataFrames from XLSX |
| Backend | FastAPI + SSE streaming |
| Frontend | React 18 + Vite + Tailwind CSS |
| Hosting | Railway (nixpacks monorepo) |

---

## Project structure

```
parcelpilot-agent/
├── backend/
│   ├── main.py               # FastAPI app, SSE endpoints
│   ├── agent.py              # Hand-rolled tool-router loop
│   ├── tools/
│   │   ├── document_search.py
│   │   ├── data_lookup.py    # SLA check, credit calc, proactive sweep
│   │   └── escalate.py
│   ├── data_loader.py        # Loads XLSX into DataFrames
│   ├── vector_store.py       # ChromaDB init, PDF ingest
│   └── confirmation_gate.py  # Single centralised confirmation gate
├── frontend/                 # React 18 + Vite + Tailwind
│   └── src/components/       # ChatPanel, ConfirmationCard, ProactivePanel…
├── showcase/                 # Standalone HTML/CSS/JS demo UI
├── sources/                  # Source PDFs + assessment XLSX
├── tests/                    # pytest (49 tests) + Vitest (5 tests)
├── data/
│   └── escalations.jsonl     # Mocked escalation log
├── PRODUCT_SHOWCASE.html     # Compass-style single-file demo
├── requirements.txt
├── nixpacks.toml             # Provisions nodejs_20 + python311
└── railway.toml
```

---

## Running locally

**Prerequisites:** Python 3.11+, Node 20+, a free [Groq API key](https://console.groq.com)

```bash
# 1. Clone
git clone https://github.com/sumitboii/parcelpilot-agent.git
cd parcelpilot-agent

# 2. Backend
cp .env.example .env
# Add your GROQ_API_KEY to .env
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev

# 4. Or open the standalone demo
# http://localhost:8000/showcase
```

**Open the demo:** `http://localhost:8000` (React app) or `http://localhost:8000/showcase` (Compass-style single-page demo)

---

## Source authority hierarchy

As defined in `01_Support_Policy_v3_CURRENT.pdf §1`:

1. Signed customer agreement (highest — overrides everything for that account)
2. Support Policy v3 — `01_Support_Policy_v3_CURRENT.pdf`
3. Cancellation & Service Credit SOP v4 / Product Operations Guide
4. Historical tickets — context only, may be wrong

`02_Support_Policy_v2_DEPRECATED.pdf` is filtered at ingest and never retrievable.

---

## Key test scenarios (all pass)

| Scenario | What the agent must do |
|---|---|
| Northstar cancel ORD-1001 | No fee — Agreement §2 overrides SOP 30-min rule; overrides wrong TKT-450 |
| LumenWorks 4,200-row CSV | Product limit 5,000 rows; KI-208 workaround 3,000; overrides wrong TKT-451 |
| TKT-504 SwiftShip BOOKED | Surface KI-211 webhook delay; don't say pickup didn't happen |
| ORD-2002 LumenWorks credit | INR 300 fixed / 4h threshold (not SOP 2h / INR 500) |
| TKT-505 Axis Labs P1 | 30-min Enterprise SLA (not Northstar's 15-min); 2h 30m breach |
| ACCT-004 no agreement | Standard Enterprise policy; don't borrow Northstar's terms |

---

## Deploying to Railway

```bash
# Set secret
railway variables set GROQ_API_KEY=<your-key>

# Deploy
railway up
```

`nixpacks.toml` explicitly provisions both `nodejs_20` and `python311` — required because `package.json` is in `frontend/`, not the repo root.
