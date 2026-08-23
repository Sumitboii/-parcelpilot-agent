/**
 * demo-data.js — pre-built demo responses for offline / file:// mode.
 *
 * Covers all 9 self-test scenarios with accurate cited answers.
 * Each generator yields events that match the live SSE event types:
 *   { type: 'tool',    name: 'document_search' | 'data_lookup' | 'escalate' }
 *   { type: 'text',    content: string }   — streamed word by word
 *   { type: 'confirm', display: {}, payload: {} }
 */

'use strict';

const DEMO_RESPONSES = {

  northstar: async function* () {
    yield { type: 'tool', name: 'data_lookup' };
    yield { type: 'tool', name: 'document_search' };
    yield {
      type: 'text',
      content:
        '**Yes — Northstar can cancel ORD-1001 with no cancellation fee.**\n\n' +
        'ORD-1001 is currently in **BOOKED** status and has not been picked up [orders: ORD-1001]. ' +
        'The Northstar Enterprise Agreement §2 explicitly waives all cancellation fees for any BOOKED-before-pickup shipment, ' +
        'regardless of how long ago it was booked [05_Northstar_Logistics_Enterprise_Agreement.pdf, p.2 §2].\n\n' +
        'This overrides the SOP default which charges INR 250 after 30 minutes [03_Cancellation_and_Service_Credit_SOP_v4.pdf, p.1 §1] ' +
        '— the signed customer agreement takes precedence at Level 1 of the source authority hierarchy.\n\n' +
        '⚠ Note: A previous agent resolution (TKT-450) incorrectly stated an INR 250 fee applied. ' +
        'That historical record is overridden by the current authoritative agreement.',
    };
  },

  tkt505: async function* () {
    yield { type: 'tool', name: 'data_lookup' };
    yield { type: 'tool', name: 'document_search' };
    yield {
      type: 'text',
      content:
        '**⚠ P1 — SLA already breached. Escalate immediately.**\n\n' +
        'TKT-505 (Axis Labs, ACCT-004) involves suspected API key exposure [tickets: TKT-505]. ' +
        'This is classified **P1** under the security incident definition [01_Support_Policy_v3_CURRENT.pdf, p.1 §2].\n\n' +
        'Axis Labs has no custom agreement in the source pack — standard Enterprise SLA applies: ' +
        '**P1 = 30 minutes, 24×7** [01_Support_Policy_v3_CURRENT.pdf, p.2 §3]. ' +
        'Ticket created at 08:30; snapshot time is 11:00 — **2h 30m elapsed**. SLA breached by 2 hours.',
    };
    yield {
      type: 'confirm',
      display: {
        Action:       'Create Escalation',
        Ticket:       'TKT-505',
        Account:      'Axis Labs (ACCT-004)',
        Severity:     'P1',
        'Assigned to': 'Rohit',
        Reason:       'API key exposure — P1 security incident. SLA breached by 2h 30m.',
      },
      payload: {
        ticket_id:   'TKT-505',
        account_id:  'ACCT-004',
        severity:    'P1',
        reason:      'Suspected API key/credential exposure — P1 security incident, SLA already breached.',
        assigned_to: 'Rohit',
        created_by:  'Demo User (demo)',
        summary:     'TKT-505 Axis Labs API key exposure. P1 classification per Policy v3 §2. Standard Enterprise 30-min SLA — 2h 30m elapsed, breached.',
      },
    };
  },

  lumenworks_credit: async function* () {
    yield { type: 'tool', name: 'data_lookup' };
    yield { type: 'tool', name: 'document_search' };
    yield {
      type: 'text',
      content:
        '**Yes — ORD-2002 is eligible for a service credit of INR 300.**\n\n' +
        'The pickup window ended at 06:30; at dataset snapshot time (11:00 IST) the delay is **4h 30m** [orders: ORD-2002]. ' +
        'This exceeds LumenWorks\'s custom 4-hour threshold [06_LumenWorks_Service_Agreement.pdf, p.2 §3]. ' +
        'Carrier fault is confirmed and there is no customer fault [orders: ORD-2002].\n\n' +
        'The LumenWorks agreement replaces the SOP default (2h threshold, INR 500/10% formula) ' +
        'with a **fixed INR 300 credit** [06_LumenWorks_Service_Agreement.pdf, p.2 §3]. ' +
        'No manager approval required (INR 300 < INR 1,000 threshold).',
    };
  },

  bulk_upload: async function* () {
    yield { type: 'tool', name: 'document_search' };
    yield {
      type: 'text',
      content:
        'The **product limit for Bulk Upload is 5,000 rows per CSV** — not 3,000 [04_Product_Operations_Guide_and_Known_Issues.pdf, p.1 §1]. ' +
        'Bulk Upload is available on Growth and Enterprise plans.\n\n' +
        '**KI-208** (opened 10 Aug 2026, status: Investigating) documents intermittent failures ' +
        'above approximately 3,000 rows [04_Product_Operations_Guide_and_Known_Issues.pdf, p.2 §2]. ' +
        'The recommended workaround is to split uploads into files below 3,000 rows. ' +
        'Individual shipment creation is unaffected.\n\n' +
        '⚠ Note: A previous agent response (TKT-451) incorrectly stated the plan limit is 3,000 rows. ' +
        'That is the KI-208 workaround threshold, not the product specification.',
    };
  },

  swiftship: async function* () {
    yield { type: 'tool', name: 'data_lookup' };
    yield { type: 'tool', name: 'document_search' };
    yield {
      type: 'text',
      content:
        'TKT-504 reports that the SwiftShip order still shows **BOOKED** approximately 10 minutes after driver collection [tickets: TKT-504].\n\n' +
        '**Do not tell the customer that pickup did not occur.** ' +
        'This matches **KI-211** (opened 12 Aug 2026, status: Monitoring): SwiftShip pickup confirmation webhooks ' +
        'can arrive up to 20 minutes late — a parcel may be physically collected while ParcelPilot still shows BOOKED ' +
        '[04_Product_Operations_Guide_and_Known_Issues.pdf, p.2 §2].\n\n' +
        '**Recommended:** Advise the customer to verify carrier status directly with SwiftShip, ' +
        'or wait through the 20-minute known delay window before concluding that pickup did not occur.',
    };
  },

  default: async function* (query) {
    yield { type: 'tool', name: 'document_search' };
    yield {
      type: 'text',
      content:
        'This is a **demo mode** response — the backend is not currently reachable from this browser.\n\n' +
        'For live responses with full cited answers, deploy the application to Railway or run the ' +
        'FastAPI backend locally (`uvicorn backend.main:app --reload` from `parcelpilot-agent/`).\n\n' +
        'Try one of the pre-built scenario chips to see a full streamed demo response with citations and tool chips.',
    };
  },
};

/**
 * Match an incoming query to the closest demo scenario key.
 * @param {string} query
 * @returns {string} key into DEMO_RESPONSES
 */
function matchDemoScenario(query) {
  const q = query.toLowerCase();
  if (q.includes('northstar') || q.includes('ord-1001') || q.includes('cancel')) return 'northstar';
  if (q.includes('tkt-505') || q.includes('api key') || q.includes('credential') || q.includes('credential')) return 'tkt505';
  if (q.includes('lumenworks') && (q.includes('credit') || q.includes('ord-2002'))) return 'lumenworks_credit';
  if (q.includes('lumenworks') || q.includes('ord-2002') || q.includes('credit')) return 'lumenworks_credit';
  if (q.includes('bulk') || q.includes('csv') || q.includes('upload') || q.includes('row')) return 'bulk_upload';
  if (q.includes('swiftship') || q.includes('tkt-504') || q.includes('booked') || q.includes('webhook')) return 'swiftship';
  return 'default';
}

const DEMO_SIDEBAR_ITEMS = [
  {
    category:          'SLA Breach',
    ticket_ids:        ['TKT-505'],
    account_name:      'Axis Labs',
    account_id:        'ACCT-004',
    recommended_action:'P1 SLA breached — 2h 30m elapsed, target 30m',
    suggested_query:   'What should I do about TKT-505?',
  },
  {
    category:          'SLA Breach',
    ticket_ids:        ['TKT-501'],
    account_name:      'Northstar Logistics',
    account_id:        'ACCT-001',
    recommended_action:'P1 SLA breached — 30m elapsed, target 15m',
    suggested_query:   'Tell me about TKT-501 and whether I should escalate',
  },
  {
    category:          'KI-Linked',
    ticket_ids:        ['TKT-502'],
    account_name:      'LumenWorks',
    account_id:        'ACCT-002',
    recommended_action:'Linked to KI-208: intermittent bulk upload failures above ~3,000 rows',
    suggested_query:   'Is TKT-502 related to KI-208? What should I tell the customer?',
  },
  {
    category:          'KI-Linked',
    ticket_ids:        ['TKT-504'],
    account_name:      'Northstar Logistics',
    account_id:        'ACCT-001',
    recommended_action:'Linked to KI-211: SwiftShip webhook delay up to 20 min',
    suggested_query:   'TKT-504 shows BOOKED but driver already picked up',
  },
  {
    category:          'Account Cluster',
    ticket_ids:        ['TKT-501', 'TKT-504'],
    account_name:      'Northstar Logistics',
    account_id:        'ACCT-001',
    recommended_action:'2 open tickets from this account in the last 7 days',
    suggested_query:   'What open tickets does Northstar Logistics have and is there a pattern?',
  },
];

const DEMO_SNAPSHOT_TIME = '2026-08-16T11:00:00+05:30';
