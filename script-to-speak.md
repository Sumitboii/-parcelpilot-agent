# 🎙️ ParcelPilot Support Agent — 10-Minute Video Demo Script (`script-to-speak.md`)

This script provides the **exact words to speak** and **on-screen actions to trigger** for a 10-minute evaluation demo video, updated with all new production features including Render deployment, multi-key health step function, zero-latency failover, and interactive live issues.

* **Primary Production URL (Render):** [https://parcelpilot-agent-05e4.onrender.com](https://parcelpilot-agent-05e4.onrender.com)
* **Secondary Production URL (Railway):** [https://parcelpilot-agent-production.up.railway.app](https://parcelpilot-agent-production.up.railway.app)
* **GitHub Repository:** [https://github.com/Sumitboii/-parcelpilot-agent](https://github.com/Sumitboii/-parcelpilot-agent)

---

## ⏱️ Timeline & Agenda Overview

| Timecode | Segment | Core Topic Demonstrated |
|---|---|---|
| **00:00 – 01:15** | **1. Introduction & Context** | Overview of ParcelPilot, support bottlenecks, and core objectives |
| **01:15 – 02:30** | **2. Architecture & Multi-Key Pool** | Plain Python tool router, multi-key health step function, zero-latency LRU |
| **02:30 – 04:15** | **3. Demo 1: Source Hierarchy & Contract Override** | Northstar cancellation query (Agreement §2 overrides Policy & bad TKT-450) |
| **04:15 – 05:45** | **4. Demo 2: Confirmation Gate & Escalation** | TKT-505 P1 incident (SLA breach check + interactive confirmation card) |
| **05:45 – 07:00** | **5. Demo 3: Service Credit Calculations** | LumenWorks delay credit (Custom agreement ₹300 fixed override) |
| **07:00 – 08:15** | **6. Demo 4: Known Issues & Deprecated Policies** | KI-208 bulk upload limit vs bug workaround & Policy v2 refusal |
| **08:15 – 09:15** | **7. Demo 5: Interactive Live Issues Radar** | Live issues sidebar (SLA breaches, KI clusters, account surges with 1-click trigger) |
| **09:15 – 10:00** | **8. Trust, Metrics & Wrap-Up** | Grounded citations, 66/66 test suite, hallucination prevention |

---

## 🎬 Detailed Script: Words to Speak & Screen Actions

---

### Segment 1: Introduction & Context `[00:00 – 01:15]`

**[SCREEN ACTION]**
* Share screen showing the clean **ParcelPilot Support Agent** UI (`https://parcelpilot-agent-05e4.onrender.com`).
* Highlight the top bar with active user role (`Rohit — Support Agent`), the central conversation area, and the left **Live Issues** sidebar.

**[WORDS TO SPEAK]**
> "Hello everyone! Today I’m excited to present the **ParcelPilot AI Support Agent** — an intelligent operational copilot built for ParcelPilot’s support and customer operations teams.
> 
> ParcelPilot coordinates logistics across multiple carriers, processing hundreds of complex enterprise queries every day. Today, support agents lose hours manually cross-referencing PDFs, custom enterprise contracts, order databases, and ticketing systems. 
> 
> The core challenge isn’t just fetching data — it’s handling **conflicts, speed, and trust**. Customer agreements override standard policies, old policies get deprecated, rate limits can cause unexpected downtime, and historical ticket resolutions often contain errors.
> 
> We built this production system to solve that exact problem: delivering sub-second, trustworthy, cited answers with automated multi-key failover while keeping humans strictly in control of critical business actions."

---

### Segment 2: Architecture & Multi-Key Health Step Function `[01:15 – 02:30]`

**[SCREEN ACTION]**
* Briefly show the top-right role selector, the clean streaming message area, and point out the sub-second streaming responsiveness.
* Open the `/docs` or mention the `/keys/health` endpoint briefly.

**[WORDS TO SPEAK]**
> "Let’s take a look at the architecture under the hood.
> 
> First, **Multi-Key Health Step Function**: To guarantee zero downtime and eliminate rate-limit disruptions, we built a custom `GroqKeyPoolManager`. It automatically discovers all available Groq API keys, dispatches requests with zero added latency using an in-memory Least-Recently-Used rotation, and includes an automated step function that fails over to a backup key in milliseconds if a 429 rate limit or 413 token limit occurs. A background worker continuously probes key health every 30 seconds.
> 
> Second, **Strict Source Authority Hierarchy**: The agent is hard-wired with a deterministic hierarchy:
> 1. Signed customer agreements always take top priority.
> 2. Current support policies (Policy v3 CURRENT) come second.
> 3. Standard SOPs and operations guides come third.
> 4. Historical ticket resolutions are treated strictly as unverified context.
> 5. Any deprecated documents — such as Support Policy v2 — are completely filtered out.
> 
> Third, **Safety & Privacy**: Every data query passes through an in-memory data store with Role-Based Access Control, and state-changing actions like escalations are intercepted by an interactive confirmation gate."

---

### Segment 3: Scenario 1 — Source Authority & Contract Override `[02:30 – 04:15]`

**[SCREEN ACTION]**
* Click the suggestion chip: **`Northstar cancellation`** (or type: `"Can Northstar cancel ORD-1001 without a fee? Explain why."`)
* Press **Send**.
* Point out the tool chips appearing (`data_lookup`, `document_search`) and the rapid token streaming.

**[WORDS TO SPEAK]**
> "Let’s test our first scenario: a contract conflict and a known bad historical record.
> 
> I’ll ask: *'Can Northstar cancel ORD-1001 without a fee?'*
> 
> Notice what happened:
> 1. The agent immediately called `data_lookup` to check `ORD-1001`. It saw the order is still in `BOOKED` status.
> 2. It then queried `document_search` for Northstar’s specific enterprise agreement.
> 
> Look at the answer:
> - The agent confirms: **Yes, Northstar can cancel with zero fee.**
> - It cites **Section 2 of Northstar’s Enterprise Agreement**, which explicitly waives all cancellation fees for shipments cancelled before pickup.
> - Most importantly, it actively highlights that a past ticket resolution — **TKT-450** — incorrectly told the customer they owed ₹250. The agent correctly rejected that historical mistake in favor of the authoritative contract.
> - Every single claim is backed by a clickable citation badge."

---

### Segment 4: Scenario 2 — Human-in-the-Loop Confirmation Gate `[04:15 – 05:45]`

**[SCREEN ACTION]**
* Click the suggestion chip: **`TKT-505 API key`** (or type: `"What should I do about TKT-505?"`)
* Press **Send**.
* Show the tool chips, the policy check, and then the interactive **⚡ Confirm Action** card rendered on screen.
* Click **Confirm** button and show the generated escalation ID (`ESC-20260816-XXXX`).

**[WORDS TO SPEAK]**
> "Now let’s look at a critical operational safety requirement: **The Confirmation Gate**.
> 
> I’m asking about **TKT-505**, a ticket reporting possible API key exposure for Axis Labs.
> 
> Notice how the agent reasons through this:
> 1. It checks the ticket: Opened at 08:30, snapshot is 11:00 — so 2 hours and 30 minutes have elapsed.
> 2. It checks policy: Axis Labs is Enterprise with no custom agreement, so Standard Policy v3 applies. P1 target is 30 minutes.
> 3. The SLA is breached by 2 hours. Because suspected credential leak is classified as **P1**, policy mandates immediate escalation.
> 
> But instead of executing the escalation silently in the background, look at the screen:
> The agent rendered an interactive **Confirmation Card** with pre-filled metadata: Ticket ID, Severity, Reason, and Assignee.
> 
> Until I click 'Confirm', nothing is written to our audit database. When I click **Confirm**, it formally logs the escalation and returns a permanent tracking ID."

---

### Segment 5: Scenario 3 — Service Credit Calculations `[05:45 – 07:00]`

**[SCREEN ACTION]**
* Click the suggestion chip: **`LumenWorks credit`** (or type: `"Is ORD-2002 eligible for a service credit?"`)
* Press **Send**.
* Highlight the calculation breakdown, delay duration, and contract override.

**[WORDS TO SPEAK]**
> "Next, let’s test mathematical calculation and custom SLA terms with **ORD-2002** for LumenWorks.
> 
> The standard ParcelPilot SOP specifies that a credit is eligible after a 2-hour delay using a 10% formula.
> 
> But watch what the agent does:
> 1. It looks up `ORD-2002`: the pickup window closed at 06:30, making the delay **4 hours and 30 minutes** due to carrier fault.
> 2. It retrieves LumenWorks’s Service Agreement.
> 3. It applies LumenWorks’s custom contract clause: their threshold is 4 hours, and instead of a variable percentage, it awards a **fixed ₹300 credit**.
> 4. It also confirms that because ₹300 is below the ₹1,000 policy threshold, manager pre-approval is not required."

---

### Segment 6: Scenario 4 — Known Issues & Guardrails `[07:00 – 08:15]`

**[SCREEN ACTION]**
* Click the suggestion chip: **`Bulk upload limit`** (or type: `"LumenWorks 4200-row CSV fails to upload"`)
* Press **Send**.
* Show how the agent distinguishes product specs from workaround limits.

**[WORDS TO SPEAK]**
> "Let’s look at how the agent handles product bugs versus real specifications.
> 
> When LumenWorks asks why their 4,200-row CSV upload failed:
> - The agent clarifies that the official product specification is **5,000 rows**.
> - But it detects known bug **KI-208**, which causes intermittent failures above 3,000 rows.
> - It provides the exact operational workaround: split the file into smaller batches under 3,000 rows while engineering deploys a fix.
> - Again, it flags that old ticket **TKT-451** incorrectly told the customer 3,000 was the plan limit, setting the record straight."

---

### Segment 7: Scenario 5 — Interactive Live Issues Radar `[08:15 – 09:15]`

**[SCREEN ACTION]**
* Move the cursor to the left **Live Issues** sidebar.
* Click on **`TKT-504`** or **`Account Cluster (Northstar)`** directly from the sidebar.
* Point out that clicking the item immediately triggers the live investigation with full AI streaming and tool chips without manual typing.

**[WORDS TO SPEAK]**
> "Now let’s look at **Proactive Issue Detection & Investigation**.
> 
> Reactive chat only helps after a human asks. Operations teams need to know what’s on fire *before* customers escalate.
> 
> On the left sidebar, our backend runs a continuous proactive sweep across all active orders and tickets:
> - **🚨 SLA Breaches:** Instantly surfaces breached tickets like TKT-505 and TKT-501 with exact elapsed times.
> - **🐛 Known Issue Clusters:** Groups tickets linked to active bugs like KI-208 and KI-211.
> - **👥 Account Clusters:** Detects when a single enterprise account has multiple complaints within 7 days.
> 
> Watch this: I can simply click **`TKT-504`** or **`Account Cluster`** directly on the sidebar. The UI immediately begins the investigation, runs the tools, and explains the correlation between the orders in real time."

---

### Segment 8: Trust, Evaluation Metrics & Wrap-Up `[09:15 – 10:00]`

**[SCREEN ACTION]**
* Scroll up through the chat transcript showing clean Markdown tables, citation badges, and confirmation records.
* Switch user role to `Priya Mehta — CSM` to demonstrate role-based session isolation.
* Show the test suite passing summary (66/66 tests passed).

**[WORDS TO SPEAK]**
> "To wrap up:
> - **Trust & Grounding:** Every single factual statement cites an authoritative document or database key. The agent never hallucinates.
> - **Speed & Resilience:** Powered by a multi-key Groq pool with zero-latency failover and a lightweight, memory-efficient in-memory vector store (< 40MB RAM).
> - **Verified Quality:** 66 out of 66 automated tests pass across unit tests, key rotation, and full evaluation scenarios.
> - **Primary North Star Metric:** We measure **Resolution Accuracy & Groundedness (% of responses with zero hallucinations and verified source hierarchy resolution)**.
> 
> Thank you for your time, and I look forward to your questions!"
