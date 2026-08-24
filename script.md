# 🎙️ ParcelPilot AI Support Copilot — Complete Voice-Over Video Recording Guide (`script.md`)

> **Recording Mode:** Screen-Share + Microphone Voice-Over (No Face Camera Needed)  
> **Target Video Duration:** 8 to 10 Minutes  
> **Production Live URL:** [https://parcelpilot-agent-05e4.onrender.com](https://parcelpilot-agent-05e4.onrender.com)  
> **Backup URL:** [https://parcelpilot-agent-production.up.railway.app](https://parcelpilot-agent-production.up.railway.app)  
> **GitHub Repo:** [https://github.com/Sumitboii/-parcelpilot-agent](https://github.com/Sumitboii/-parcelpilot-agent)

---

## ⚠️ Important Rules While Recording:
* 🖱️ **`[ON-SCREEN ACTION]`**: What you click with your mouse or type into the search box.
* 🗣️ **`[WHAT TO SPEAK INTO YOUR MIC]`**: Read these words out loud with your voice. **Do NOT type these sentences into the chatbot!**
* 📉 **Live Counter**: Watch the top-left sidebar count tick down from **`5 ➔ 4 ➔ 3 ➔ 2 ➔ 1 ➔ 0`** as you resolve each live issue.

---

## ⏱️ Step-by-Step Recording Walkthrough

---

### 📍 Scene 1: Introduction & System Overview `[00:00 – 01:15]`

#### 🖱️ [ON-SCREEN ACTION]:
1. Open your browser in full screen (`F11`) at: `https://parcelpilot-agent-05e4.onrender.com`.
2. Move your mouse slowly across the top header: hover over the green **`Connected`** badge and the active user **`Rohit — Support Agent`**.
3. Move your mouse to the left sidebar: point at the red **`Live Issues`** badge showing **`5`**.
4. Hover your mouse over the suggestion chips in the center of the screen.

#### 🗣️ [WHAT TO SPEAK INTO YOUR MIC]:
> "Hello everyone! Welcome to this demonstration of the **ParcelPilot AI Support Copilot** — an operational AI platform purpose-built for freight and parcel logistics support.
> 
> In logistics, support teams process hundreds of complex queries daily: order tracking delays, fee disputes, API outages, and SLA calculations.
> 
> The core challenge in this domain is **authority and trust**. Signed enterprise contracts override standard policies, old SOPs get deprecated, rate-limits disrupt automated tools, and historical tickets often contain human errors.
> 
> We built ParcelPilot to solve these exact problems: delivering cited, sub-second answers while enforcing a locked 4-tier source authority hierarchy and keeping human agents strictly in control of critical actions.
> 
> Notice on the top-left sidebar: our proactive scanner has automatically detected **5 Live Issues** that need immediate attention. Let’s look at the engine and resolve every single one of them."

---

### 📍 Scene 2: Architecture & Multi-Key Health Pool `[01:15 – 02:30]`

#### 🖱️ [ON-SCREEN ACTION]:
1. Keep the main chat interface on screen. Move your mouse cursor slightly over the message area.

#### 🗣️ [WHAT TO SPEAK INTO YOUR MIC]:
> "Before running our queries, let's look at the architecture behind this platform.
> 
> First, **Multi-Key Health Step Function**: To guarantee zero downtime on cloud instances, we built an in-memory `GroqKeyPoolManager`. It automatically discovers all active API keys, routes queries with zero-latency Least-Recently-Used rotation, and includes an automated step function that fails over in milliseconds if a 429 rate limit occurs. A background worker continuously probes key health every 30 seconds.
> 
> Second, **Locked Source-Authority Hierarchy**: The agent strictly enforces a 4-tier authority rule:
> - **Level 1**: Signed Customer Agreements take top priority and override general rules for that account.
> - **Level 2**: Current Support Policy Version 3 comes second.
> - **Level 3**: Standard Operating Procedures and Product Guides come third.
> - **Level 4**: Historical Ticket Resolutions are treated strictly as unverified context — any known historical error is actively overridden.
> - Deprecated documents — like Policy Version 2 — are permanently purged during vector ingestion.
> 
> Third, **Safety & Confirmation Gate**: State-changing actions like ticket escalations are intercepted by an interactive confirmation card before touching the database."

---

### 📍 Scene 3: Foundational Query — Contract Precedence & Cancellation `[02:30 – 03:45]`

#### 🖱️ [ON-SCREEN ACTION]:
1. In the central chat area, click the suggestion chip: **`Northstar cancellation`** *(or type: `Can Northstar cancel ORD-1001 without a fee? Explain why.` into the input box and press Enter)*.
2. Point your mouse at the animated **`ParcelPilot · Compass`** workflow card showing `data_lookup (0.3s)` and `document_search (1.4s)`.
3. Highlight the formatted response, the clickable citation badges, and the rejection of legacy ticket `TKT-450`.

#### 🗣️ [WHAT TO SPEAK INTO YOUR MIC]:
> "Let’s start with a classic contract conflict scenario.
> 
> I’ll ask: *'Can Northstar cancel ORD-1001 without a fee? Explain why.'*
> 
> Watch the Compass workflow card execute in real-time:
> 1. It calls `data_lookup` to check `ORD-1001` — confirming the order is in `BOOKED` status and has not been picked up.
> 2. It queries `document_search` for Northstar’s specific enterprise contract.
> 
> Look at the answer:
> - The agent confirms: **Yes, Northstar can cancel with zero fee.**
> - It cites **Section 2 of Northstar’s Enterprise Agreement**, which explicitly waives all cancellation fees for shipments cancelled before pickup.
> - Crucially, it highlights that a legacy ticket — **TKT-450** — incorrectly charged the customer ₹250. The agent correctly rejected that historical mistake in favor of the signed contract.
> - Every claim includes an exact citation badge."

---

### 📍 Scene 4: Live Issue 1 — TKT-505 Axis Labs P1 SLA Breach `[03:45 – 05:00]`
*(Live Issues Counter: Drops from 5 ➔ 4)*

#### 🖱️ [ON-SCREEN ACTION]:
1. Move your mouse to the left sidebar: point at the counter showing **`5`**.
2. Click the top sidebar item: **`TKT-505 — Axis Labs`** *(or click chip `TKT-505 API key`)*.
3. Watch the agent stream the analysis and render the blue **⚡ Confirm Action** card.
4. Hover over the fields on the confirmation card: Ticket `TKT-505`, Severity `P1`, Reason, Assignee.
5. Click the blue **`Confirm`** button.
6. Watch the card change to `✓ Confirmed` with ID `ESC-20260816-XXXX`.
7. **Point your mouse to the top-left sidebar**: Show that **`TKT-505` is now green with `✓ RESOLVED`**, and the **counter decremented from 5 to 4**.

#### 🗣️ [WHAT TO SPEAK INTO YOUR MIC]:
> "Now let's resolve our first live issue on the sidebar: **TKT-505 for Axis Labs**.
> 
> I’ll click **`TKT-505`** directly on the left sidebar.
> 
> The agent analyzes this incident:
> 1. It checks the timestamps: Created at 08:30 IST, snapshot is 11:00 IST — **2 hours and 30 minutes have elapsed**.
> 2. For suspected API key exposure on an Enterprise account, Support Policy v3 mandates a **P1 classification with a 30-minute response target**.
> 3. The SLA has been **breached by 2 hours**.
> 
> Notice how the agent doesn't silently alter data. It rendered an interactive **Confirmation Card**.
> 
> I’ll click **Confirm**.
> 
> The escalation is written directly to our audit log with an official tracking ID.
> 
> And look at our sidebar: **TKT-505 turns green with a `✓ RESOLVED` badge, and our Live Issues counter drops from 5 to 4!**"

---

### 📍 Scene 5: Live Issue 2 — TKT-501 Northstar P1 SLA Breach `[05:00 – 06:15]`
*(Live Issues Counter: Drops from 4 ➔ 3)*

#### 🖱️ [ON-SCREEN ACTION]:
1. On the left sidebar, click the next item: **`TKT-501 — Northstar Logistics`**.
2. Watch the agent retrieve Northstar’s contract and detect the expedited 15-min SLA.
3. Observe the rendered **⚡ Confirm Action** escalation card assigned to *Lead Integrations Engineer*.
4. Click the blue **`Confirm`** button.
5. **Point your mouse to the top-left sidebar**: Show that **`TKT-501` is marked `✓ RESOLVED`** and the **counter decremented from 4 to 3**.

#### 🗣️ [WHAT TO SPEAK INTO YOUR MIC]:
> "Let’s resolve our second live issue: **TKT-501 for Northstar Logistics**.
> 
> I’ll click **`TKT-501`** on the sidebar.
> 
> Here we see another critical contract override:
> 1. Standard policy allows 30 minutes for P1 incidents.
> 2. But Northstar’s signed agreement **Section 4** guarantees an expedited **15-minute response target**.
> 3. The ticket was opened at 10:30 IST (30 minutes elapsed), meaning the SLA is **breached by 15 minutes**.
> 
> The agent generates an escalation card targeted to the Lead Integrations Engineer.
> 
> I click **Confirm**.
> 
> Look at the sidebar: **TKT-501 is now marked `✓ RESOLVED`, and the counter decrements from 4 to 3!**"

---

### 📍 Scene 6: Live Issue 3 — TKT-502 LumenWorks KI-208 Workaround `[06:15 – 07:15]`
*(Live Issues Counter: Drops from 3 ➔ 2)*

#### 🖱️ [ON-SCREEN ACTION]:
1. On the left sidebar, click **`TKT-502 — LumenWorks`** *(or click chip `Bulk upload limit`)*.
2. Watch the agent run `data_lookup` and `document_search`.
3. Hover over the explanation differentiating the **5,000-row product limit** from the **KI-208 bug workaround**.
4. **Point your mouse to the top-left sidebar**: Show that **`TKT-502` is marked `✓ RESOLVED`** and the **counter decremented from 3 to 2**.

#### 🗣️ [WHAT TO SPEAK INTO YOUR MIC]:
> "Now let’s look at our third issue: **TKT-502 for LumenWorks**, reporting a bulk upload failure on a 4,200-row CSV.
> 
> I’ll click **`TKT-502`** on the sidebar.
> 
> Look at how cleanly the agent separates product specifications from temporary bugs:
> 1. It cites the official Product Operations Guide: the true product capacity is **5,000 rows per CSV**.
> 2. But it identifies active bug **KI-208**, which causes intermittent 504 timeouts on files above ~3,000 rows.
> 3. It gives the exact customer communication: advise the customer to split their 4,200-row file into two batches of 2,100 rows while engineering patches the parser.
> 4. It also rejects legacy ticket **TKT-451**, which erroneously told the customer 3,000 was their plan ceiling.
> 
> And look at the sidebar: **TKT-502 turns green with `✓ RESOLVED`, and the counter drops from 3 to 2!**"

---

### 📍 Scene 7: Live Issue 4 — TKT-504 SwiftShip Pickup Lag (KI-211) `[07:15 – 08:15]`
*(Live Issues Counter: Drops from 2 ➔ 1)*

#### 🖱️ [ON-SCREEN ACTION]:
1. On the left sidebar, click **`TKT-504 — Northstar Logistics`** *(SwiftShip pickup lag)*.
2. Watch the agent evaluate `ORD-1001` and retrieve Known Issue **KI-211**.
3. Hover over the guardrail instruction: *Do not tell the customer pickup failed*.
4. **Point your mouse to the top-left sidebar**: Show that **`TKT-504` is marked `✓ RESOLVED`** and the **counter decremented from 2 to 1**.

#### 🗣️ [WHAT TO SPEAK INTO YOUR MIC]:
> "Our fourth live issue is **TKT-504**: a customer reports that the SwiftShip driver collected their parcel 10 minutes ago, but the portal still shows `BOOKED`.
> 
> I’ll click **`TKT-504`** on the sidebar.
> 
> Watch the agent’s reasoning:
> - A naive assistant might assume the pickup failed and trigger an unnecessary redelivery.
> - But our agent identifies **Known Issue KI-211**: SwiftShip pickup confirmation webhooks experience an upstream carrier delay of up to **20 minutes**.
> - It instructs the support agent: **Do not tell the customer pickup failed.** Advise them to wait for the 20-minute webhook window to expire or check carrier tracking directly.
> 
> Look at the sidebar: **TKT-504 is marked `✓ RESOLVED`, and the counter drops from 2 to 1!**"

---

### 📍 Scene 8: Live Issue 5 — Northstar Account Cluster Pattern `[08:15 – 09:15]`
*(Live Issues Counter: Drops from 1 ➔ 0 — All 5 Live Issues Resolved!)*

#### 🖱️ [ON-SCREEN ACTION]:
1. On the left sidebar, click the final item: **`Account Cluster — Northstar Logistics`**.
2. Watch the agent correlate `TKT-501` and `TKT-504` into an integrated root cause summary table.
3. **Point your mouse to the top-left sidebar**: Show that **Account Cluster is marked `✓ RESOLVED`**, the counter badge displays **`0`** in bright green, and the celebratory toast appears: `🎉 All 5 Live Issues Resolved!`.

#### 🗣️ [WHAT TO SPEAK INTO YOUR MIC]:
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

### 📍 Scene 9: Service Credit Calculation & Conclusion `[09:15 – 10:00]`

#### 🖱️ [ON-SCREEN ACTION]:
1. In the input box at the bottom, type: **`Is ORD-2002 eligible for a service credit?`** and click **Send** *(or press Enter)*.
2. Watch the agent calculate the delay of 4h 30m and award the **fixed INR 300 credit** under LumenWorks Agreement §3.
3. In the top right header, click the user dropdown and switch from `Rohit — Support Agent` to **`Priya Mehta — CSM / Escalation Manager`** to demonstrate Role-Based Access Control.
4. Scroll up smoothly through the clean conversation transcript on your screen.

#### 🗣️ [WHAT TO SPEAK INTO YOUR MIC] *(Speak out loud — do NOT type this in chat!)*:
> "Finally, let’s test mathematical contract overrides with: *'Is ORD-2002 eligible for a service credit?'*
> 
> - The agent calculates the delay: **4 hours and 30 minutes**.
> - It applies Section 3 of the **LumenWorks Service Agreement**, which overrides the SOP percentage formula with a **fixed INR 300 credit**.
> - It verifies that because ₹300 is under ₹1,000, no manager pre-approval is required.
> 
> To wrap up what we’ve demonstrated today:
> - **100% Grounded Citations** with zero hallucination.
> - **Multi-Key Groq Key Pool** with zero-latency failover and sub-40MB memory footprint.
> - **Human Confirmation Gates** for critical operational state changes.
> - **Proactive Triage & Live Issue Tracking** from 5 down to 0.
> - **66 out of 66 automated tests passing** across our full evaluation benchmark.
> 
> Thank you for watching!"
