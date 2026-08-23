/**
 * ConfirmationCard.tsx — Inline confirmation card for state-changing actions.
 * Rendered inside the chat stream (NOT a modal).
 * Both buttons disable immediately on click to prevent double-submission.
 */
import { useState } from "react";

export interface PendingAction {
  type: "pending_confirmation";
  action: string;
  display: Record<string, string>;
  payload: Record<string, unknown>;
}

interface ConfirmationCardProps {
  action: PendingAction;
  sessionId: string;
  onResult: (result: "confirmed" | "cancelled", escalationId?: string) => void;
}

export function ConfirmationCard({ action, sessionId, onResult }: ConfirmationCardProps) {
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    setSubmitted(true);
    setLoading(true);
    try {
      const res = await fetch("/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          confirm: true,
          payload: action.payload,
        }),
      });
      const data = await res.json();
      onResult("confirmed", data.escalation_id);
    } catch {
      onResult("confirmed");
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    setSubmitted(true);
    try {
      await fetch("/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, confirm: false }),
      });
    } catch {
      // ignore
    }
    onResult("cancelled");
  };

  return (
    <div
      className="rounded-r-lg p-4 text-sm"
      style={{
        background: "#111111",
        borderLeft: "4px solid #2563eb",
        border: "1px solid rgba(255,255,255,0.05)",
        borderLeftWidth: "4px",
        borderLeftColor: "#2563eb",
      }}
    >
      <p className="text-xs font-semibold mb-3" style={{ color: "#2563eb" }}>
        ⚡ Confirm Action
      </p>

      <dl className="space-y-1 mb-4">
        {Object.entries(action.display).map(([key, val]) => (
          <div key={key} className="flex gap-2">
            <dt className="text-xs font-medium w-24 shrink-0" style={{ color: "rgba(245,245,245,0.5)" }}>
              {key}
            </dt>
            <dd className="text-xs" style={{ color: "#f5f5f5" }}>
              {val}
            </dd>
          </div>
        ))}
      </dl>

      <div className="flex gap-2">
        <button
          onClick={handleConfirm}
          disabled={submitted}
          className="px-4 py-1.5 rounded-md text-xs font-semibold transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ background: "#2563eb", color: "#fff" }}
        >
          {loading ? "Creating…" : "Confirm"}
        </button>
        <button
          onClick={handleCancel}
          disabled={submitted}
          className="px-4 py-1.5 rounded-md text-xs font-semibold transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: "transparent",
            color: "#f5f5f5",
            border: "1px solid rgba(255,255,255,0.2)",
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
