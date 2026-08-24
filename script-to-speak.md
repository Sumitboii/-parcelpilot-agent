# 🎙️ ParcelPilot Support Agent — Complete Step-by-Step Video Demo Script (`script-to-speak.md`)

This document provides the **verbatim words to speak** and **exact step-by-step on-screen actions** for a complete 10-minute evaluation demo video. It includes the step-by-step resolution of every query and demonstrates the **Live Issues Counter decrementing from 5 → 4 → 3 → 2 → 1 → 0** on the top-left sidebar as each issue is resolved.

* **Primary Production URL (Render):** [https://parcelpilot-agent-05e4.onrender.com](https://parcelpilot-agent-05e4.onrender.com)
* **Secondary Production URL (Railway):** [https://parcelpilot-agent-production.up.railway.app](https://parcelpilot-agent-production.up.railway.app)
* **GitHub Repository:** [https://github.com/Sumitboii/-parcelpilot-agent](https://github.com/Sumitboii/-parcelpilot-agent)

---

## ⏱️ Timeline & Agenda Overview

| Timecode | Segment | Core Demonstration & Live Issue State |
|---|---|---|
| **00:00 – 01:15** | **1. Introduction & Executive Context** | Overview of ParcelPilot, support bottlenecks, and live UI layout *(5 Live Issues)* |
| **01:15 – 02:30** | **2. Architecture & Multi-Key Pool** | Plain Python tool router, Groq multi-key health step function, zero-latency LRU |
| **02:30 – 03:45** | **3. Foundational: Contract Override** | Northstar cancellation query (Agreement §2 overrides Policy & bad TKT-450) |
| **03:45 – 05:00** | **4. Live Issue 1: TKT-505 Axis Labs P1 SLA** | P1 SLA breach triage + interactive confirmation card ➔ **Count drops: 5 → 4** |
| **05:00 – 06:15** | **5. Live Issue 2: TKT-501 Northstar P1 SLA** | Agreement 15-min SLA breach + escalation confirmation ➔ **Count drops: 4 → 3** |
| **06:15 – 07:15** | **6. Live Issue 3: TKT-502 LumenWorks KI-208** | KI-208 bulk upload limit vs bug workaround ➔ **Count drops: 3 → 2** |
| **07:15 – 08:15** | **7. Live Issue 4: TKT-504 SwiftShip KI-211** | SwiftShip 20-min webhook delay explanation ➔ **Count drops: 2 → 1** |
| **08:15 – 09:15** | **8. Live Issue 5: Account Cluster Pattern** | Cross-ticket correlation between TKT-501 & TKT-504 ➔ **Count drops: 1 → 0 (All Resolved)** |
| **09:15 – 10:00** | **9. Trust, Metrics & Wrap-Up** | Grounded citations, 66/66 test suite, hallucination prevention |

---

## 🎬 Detailed Step-by-Step Script: Words to Speak & Screen Actions

---

### Segment 1: Introduction & Executive Context `[00:00 – 01:15]`

#### 🖥️ Step-by-Step On-Screen Actions:
1. Open browser tab to the live deployment: `https://parcelpilot-agent-05e4.onrender.com`.
2. Move cursor to the top bar: point out the active role indicator (**`Rohit — Support Agent`**) and the green **Connected** status badge.
3. Move cursor to the left sidebar: highlight the **Live Issues** component showing **`5`** active items in red/amber badges.
4. Hover over the central conversation area showing the empty state suggestion chips.

#### 🗣️ Exact Words to Speak:
> "Hello everyone! Today I’m excited to present the **ParcelPilot AI Support Copilot** — an enterprise-grade operational assistant built for ParcelPilot’s support and customer success teams.
> 
> ParcelPilot coordinates freight and parcel deliveries across multiple logistics carriers, processing hundreds of complex queries daily. Today, support agents lose hours manually cross-referencing multi-page PDFs, custom enterprise contracts, order spreadsheets, and legacy ticketing records.
> 
> The hardest part of this domain isn’t just fetching data — it’s handling **authority conflicts, speed, and trust**. Customer agreements override standard policies, old policies get deprecated, rate limits cause unexpected service outages, and historical ticket resolutions often contain errors.
> 
> We built this production system to solve those exact operational headaches: delivering sub-second, trustworthy, cited answers with automated multi-key failover while keeping human agents strictly in control of critical business actions.
> 
> Notice on the top-left sidebar: our proactive radar has automatically surfaced **5 Live Issues** that need our attention. Let's look at how the system works under the hood and resolve every single one of them."

---

### Segment 2: Architecture & Multi-Key Health Step Function `[01:15 – 02:30]`

#### 🖥️ Step-by-Step On-Screen Actions:
1. Scroll slightly or open developer tools / docs tab showing API endpoints (`/health`, `/chat`, `/proactive`).
2. Point out the sub-second streaming response capability and zero-framework lean architecture.
3. Move back to the main chat window ready to trigger queries.

#### 🗣️ Exact Words to Speak:
> "Let’s take a quick look at the architecture powering ParcelPilot.
> 
> First, **Multi-Key Health Step Function**: To guarantee zero downtime and eliminate rate-limit disruptions, we built a custom `GroqKeyPoolManager`. It automatically discovers all available Groq API keys, dispatches requests with zero added latency using an in-memory Least-Recently-Used rotation, and includes an automated step function that fails over to a backup key in milliseconds if a 429 rate limit occurs. A background worker continuously probes key health every 30 seconds.
> 
> Second, **Locked Source-Authority Hierarchy**: The agent enforces a deterministic 4-tier precedence hierarchy:
> 1. Level 1: **Signed Customer Agreements** always take top priority and override general rules for that specific account.
> 2. Level 2: **Current Support Policies** (`01_Support_Policy_v3_CURRENT.pdf`) come second.
> 3. Level 3: **Standard Operating Procedures (SOPs)** and operations guides come third.
> 4. Level 4: **Historical Ticket Resolutions** are treated strictly as unverified context — any known historical error is actively rejected.
> 5. Any deprecated documents — such as `02_Support_Policy_v2_DEPRECATED.pdf` — are completely filtered out.
> 
> Third, **Safety & Privacy**: Every data query passes through an in-memory data store with Role-Based Access Control, and state-changing actions like escalations are intercepted by an interactive confirmation gate."

---

### Segment 3: Foundational Demo — Source Hierarchy & Contract Override `[02:30 – 03:45]`

#### 🖥️ Step-by-Step On-Screen Actions:
1. In the central chat area, click the suggestion chip: **`Northstar cancellation`** (or type: `"Can Northstar cancel ORD-1001 without a fee? Explain why."`).
2. Press **Enter** or click **Send**.
3. Point out the workflow card appearing with animated tool chips: `data_lookup` and `document_search`.
4. Highlight the formatted Markdown answer, the cited contract section, and the explicit rejection of legacy ticket `TKT-450`.

#### 🗣️ Exact Words to Speak:
> "Let’s begin with a foundational contract conflict scenario.
> 
> I’ll ask: *'Can Northstar cancel ORD-1001 without a fee? Explain why.'*
> 
> Watch the execution flow:
> 1. The agent calls `data_lookup` to check `ORD-1001`. It verifies that the order is still in `BOOKED` status and has not been dispatched.
> 2. It queries `document_search` for Northstar’s specific enterprise agreement.
> 
> Look at the answer:
> - The agent confirms: **Yes, Northstar can cancel with zero fee.**
> - It cites **Section 2 of Northstar’s Enterprise Agreement**, which explicitly waives all cancellation fees for shipments cancelled before pickup.
> - Most importantly, it actively points out that a past ticket resolution — **TKT-450** — incorrectly charged the customer ₹250. The agent correctly rejected that historical mistake in favor of the authoritative signed contract.
> - Every single claim is backed by a clickable citation badge."

---

### Segment 4: Live Issue 1 — TKT-505 Axis Labs P1 SLA Breach `[03:45 – 05:00]`
*(Live Issues Count: 5 ➔ 4)*

#### 🖥️ Step-by-Step On-Screen Actions:
1. Direct attention to the left sidebar showing **`5`** in the issue counter.
2. Click the top sidebar item: **`TKT-505 — Axis Labs`** (or click chip `TKT-505 API key`).
3. Watch the agent stream the SLA calculation, classify as **P1**, and generate the interactive **⚡ Confirm Action** card.
4. Click the blue **Confirm** button on the confirmation card.
5. Point out the green confirmation message: `✓ Escalation created: ESC-20260816-XXXX`.
6. **Point to the top-left sidebar**: Show that **TKT-505 is now marked with `✓ RESOLVED`** and the **counter decremented from 5 to 4**.

#### 🗣️ Exact Words to Speak:
> "Now let’s tackle our first live issue on the left sidebar: **TKT-505 for Axis Labs**.
> 
> I’ll click **`TKT-505`** directly on the sidebar.
> 
> Notice how the agent analyzes this incident:
> 1. It checks the ticket timestamps: Opened at 08:30 IST, snapshot is 11:00 IST — **2 hours and 30 minutes have elapsed**.
> 2. It checks governing policy: Axis Labs is an Enterprise account with no custom agreement, so Standard Policy v3 applies. For suspected API key / credential exposure, the classification is **P1**, with a strict **30-minute response target**.
> 3. The SLA is **breached by 2 hours**. Policy mandates immediate escalation and key revocation.
> 
> But instead of silently modifying the database, look at the screen:
> The agent rendered an interactive **Confirmation Card** with structured fields: Ticket ID, Severity, Reason, and Assignee.
> 
> I will now click **Confirm**.
> 
> The escalation is written to our audit log with ID `ESC-20260816-0001`.
> 
> And look at the top-left sidebar: **TKT-505 is immediately marked `✓ RESOLVED` with a green badge, and our Live Issues counter drops from 5 to 4!**"

---

### Segment 5: Live Issue 2 — TKT-501 Northstar P1 SLA Breach `[05:00 – 06:15]`
*(Live Issues Count: 4 ➔ 3)*

#### 🖥️ Step-by-Step On-Screen Actions:
1. In the left sidebar, click the next item: **`TKT-501 — Northstar Logistics`**.
2. Watch the agent retrieve Northstar’s agreement, detect the 15-min P1 target, and calculate the 15-minute breach.
3. Observe the rendered **⚡ Confirm Action** escalation card assigned to *Lead Integrations Engineer*.
4. Click the **Confirm** button.
5. **Point to the top-left sidebar**: Show that **TKT-501 is marked with `✓ RESOLVED`** and the **counter decremented from 4 to 3**.

#### 🗣️ Exact Words to Speak:
> "Let’s resolve our second live issue: **TKT-501 for Northstar Logistics**.
> 
> I’ll click **`TKT-501`** on the sidebar.
> 
> Here we see another critical contract override:
> 1. Standard Enterprise policy allows 30 minutes for P1 incidents.
> 2. But Northstar’s signed agreement **Section 4** guarantees an expedited **15-minute response target**.
> 3. The ticket was opened at 10:30 IST (30 minutes elapsed), meaning the SLA is **breached by 15 minutes**.
> 
> The agent immediately generates an escalation card targeted to the Lead Integrations Engineer.
> 
> I click **Confirm**.
> 
> The escalation is logged, and notice our sidebar: **TKT-501 is now marked `✓ RESOLVED`, and the counter decrements from 4 to 3!**"

---

### Segment 6: Live Issue 3 — TKT-502 LumenWorks KI-208 Bug Workaround `[06:15 – 07:15]`
*(Live Issues Count: 3 ➔ 2)*

#### 🖥️ Step-by-Step On-Screen Actions:
1. In the left sidebar, click **`TKT-502 — LumenWorks`** (or click chip `Bulk upload limit`).
2. Watch the agent run `data_lookup` on ticket `TKT-502` and `document_search` on the Product Operations Guide.
3. Highlight the distinction between the **5,000-row product limit** and the **KI-208 bug workaround (split below 3,000 rows)**.
4. **Point to the top-left sidebar**: Show that **TKT-502 is marked with `✓ RESOLVED`** and the **counter decremented from 3 to 2**.

#### 🗣️ Exact Words to Speak:
> "Now let’s look at our third issue: **TKT-502 for LumenWorks**, reporting a bulk upload failure on a 4,200-row CSV.
> 
> I’ll click **`TKT-502`** on the sidebar.
> 
> Look at how intelligently the agent separates product specifications from temporary bugs:
> 1. It cites the official Product Operations Guide: the true product capacity is **5,000 rows per CSV**.
> 2. But it identifies active bug **KI-208**, which causes intermittent 504 gateway timeouts on files above ~3,000 rows.
> 3. It gives the exact customer communication: advise the customer to split their 4,200-row file into two batches of 2,100 rows while engineering patches the parser.
> 4. It also rejects legacy ticket **TKT-451**, which erroneously told the customer 3,000 was their plan ceiling.
> 
> With that resolved, look at the sidebar: **TKT-502 turns green with `✓ RESOLVED`, and the counter drops from 3 to 2!**"

---

### Segment 7: Live Issue 4 — TKT-504 SwiftShip Webhook Lag (KI-211) `[07:15 – 08:15]`
*(Live Issues Count: 2 ➔ 1)*

#### 🖥️ Step-by-Step On-Screen Actions:
1. In the left sidebar, click **`TKT-504 — Northstar Logistics`** (SwiftShip pickup lag).
2. Watch the agent evaluate order `ORD-1001` and retrieve Known Issue **KI-211**.
3. Highlight the explicit guardrail: **Do not conclude pickup failed**.
4. **Point to the top-left sidebar**: Show that **TKT-504 is marked with `✓ RESOLVED`** and the **counter decremented from 2 to 1**.

#### 🗣️ Exact Words to Speak:
> "Our fourth live issue is **TKT-504**: a ticket where the customer says the SwiftShip driver collected the parcel 10 minutes ago, but the portal still shows `BOOKED`.
> 
> I’ll click **`TKT-504`** on the sidebar.
> 
> Watch the agent’s reasoning:
> - A naive agent might assume the pickup failed and trigger an unnecessary redelivery.
> - But our agent identifies **Known Issue KI-211**: SwiftShip pickup confirmation webhooks experience an upstream carrier delay of up to **20 minutes**.
> - It instructs the support agent: **Do not tell the customer pickup failed.** Advise them to wait for the 20-minute webhook window to expire or check carrier tracking directly.
> 
> As the response completes: **TKT-504 is marked `✓ RESOLVED`, and the Live Issues counter drops from 2 to 1!**"

---

### Segment 8: Live Issue 5 — Account Cluster Pattern Analysis `[08:15 – 09:15]`
*(Live Issues Count: 1 ➔ 0 — All Issues Resolved!)*

#### 🖥️ Step-by-Step On-Screen Actions:
1. In the left sidebar, click the final item: **`Account Cluster — Northstar Logistics`**.
2. Watch the agent synthesize open tickets across `TKT-501` and `TKT-504` into an integrated account pattern table.
3. **Point to the top-left sidebar**: Show that **Account Cluster is marked with `✓ RESOLVED`**, the counter badge displays **`0`** in bright green, and the success toast appears: `🎉 All 5 Live Issues Resolved!`.

#### 🗣️ Exact Words to Speak:
> "Now let's resolve our final live issue: **Account Cluster for Northstar Logistics**.
> 
> I’ll click **`Account Cluster`** on the sidebar.
> 
> Operations leads need cross-ticket visibility. The agent analyzes Northstar’s account history:
> - It correlates **TKT-501** (webhook verification failure) and **TKT-504** (tracking status lag).
> - It identifies the root cause: an integration sync degradation between Northstar’s dispatch automation and SwiftShip carrier webhooks.
> - It recommends assigning both tickets to the same technical specialist to prevent duplicate troubleshooting.
> 
> And look at the top-left sidebar:
> **The counter reaches 0, the badge turns solid green, and all 5 Live Issues are completely resolved!**"

---

### Segment 9: Trust, Evaluation Metrics & Wrap-Up `[09:15 – 10:00]`

#### 🖥️ Step-by-Step On-Screen Actions:
1. Scroll through the conversation showing clean Markdown tables, green confirmation cards, and citation badges.
2. In the top right, switch the role dropdown to **`Priya Mehta — CSM / Escalation Manager`** to show role-based access control.
3. Show the automated test suite benchmark passing **66/66 tests**.

#### 🗣️ Exact Words to Speak:
> "To summarize what we’ve seen:
> - **100% Grounded & Cited:** Every single answer cites the authoritative signed agreement, policy PDF, or database record. The agent never hallucinates.
> - **Speed & High Availability:** Powered by our multi-key Groq pool with zero-latency failover and a lightweight in-memory vector store that runs comfortably in under 40 megabytes of RAM.
> - **Human Control:** High-impact state changes are protected behind interactive confirmation cards.
> - **Proactive Operations:** Automated SLA breach detection and known issue grouping with live tracking from 5 down to 0.
> - **Verified Quality:** 66 out of 66 automated tests pass across unit tests, key rotation, and full evaluation matrices.
> 
> Thank you for your time, and I look forward to your questions!"
