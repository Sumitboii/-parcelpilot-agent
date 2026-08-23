/**
 * ProactivePanel.tsx — Sidebar panel showing live issue detection sweep.
 * Calls GET /proactive on mount. Each item is clickable to pre-populate the chat.
 */
import { useEffect, useState } from "react";

export interface ProactiveItem {
  category: "SLA Breach" | "Approaching SLA" | "P1/P2 Open" | "Account Cluster" | "KI-Linked";
  ticket_ids: string[];
  account_id: string;
  account_name: string;
  recommended_action: string;
  suggested_query: string;
}

const CATEGORY_CONFIG: Record<string, { icon: string; color: string }> = {
  "SLA Breach":     { icon: "🚨", color: "#ef4444" },
  "Approaching SLA":{ icon: "⏰", color: "#f59e0b" },
  "P1/P2 Open":     { icon: "🔴", color: "#ef4444" },
  "Account Cluster":{ icon: "👥", color: "#8b5cf6" },
  "KI-Linked":      { icon: "🐛", color: "#f59e0b" },
};

interface ProactivePanelProps {
  onPrePopulate: (query: string) => void;
}

export function ProactivePanel({ onPrePopulate }: ProactivePanelProps) {
  const [items, setItems] = useState<ProactiveItem[]>([]);
  const [snapshotTime, setSnapshotTime] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/proactive")
      .then((r) => r.json())
      .then((data) => {
        setItems(data.items ?? []);
        setSnapshotTime(data.snapshot_time ?? "");
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Group by category
  const grouped = items.reduce<Record<string, ProactiveItem[]>>((acc, item) => {
    (acc[item.category] ??= []).push(item);
    return acc;
  }, {});

  return (
    <aside
      className="flex flex-col h-full overflow-hidden"
      style={{ background: "#111111", borderRight: "1px solid rgba(255,255,255,0.05)" }}
    >
      {/* Header */}
      <div
        className="px-4 py-3 flex items-center justify-between shrink-0"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}
      >
        <span className="text-xs font-semibold" style={{ color: "#f5f5f5" }}>
          ⚡ Live Issues
        </span>
        {items.length > 0 && (
          <span
            className="text-xs rounded-full px-1.5 py-0.5"
            style={{ background: "#ef4444", color: "#fff" }}
          >
            {items.length}
          </span>
        )}
      </div>

      {/* Items */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-3">
        {loading ? (
          <p className="text-xs py-4 text-center" style={{ color: "rgba(245,245,245,0.4)" }}>
            Loading…
          </p>
        ) : items.length === 0 ? (
          <p className="text-xs py-4 text-center" style={{ color: "rgba(245,245,245,0.4)" }}>
            ✓ No active issues detected
          </p>
        ) : (
          Object.entries(grouped).map(([category, catItems]) => {
            const cfg = CATEGORY_CONFIG[category] ?? { icon: "•", color: "#f5f5f5" };
            return (
              <div key={category}>
                <p className="text-xs font-semibold mb-1.5 flex items-center gap-1" style={{ color: cfg.color }}>
                  {cfg.icon} {category}
                </p>
                <div className="space-y-1.5">
                  {catItems.map((item) => (
                    <button
                      key={item.ticket_ids.join(",")}
                      onClick={() => onPrePopulate(item.suggested_query)}
                      className="w-full text-left rounded-md px-3 py-2 text-xs transition-colors hover:opacity-80"
                      style={{
                        background: "#0a0a0a",
                        border: "1px solid rgba(255,255,255,0.05)",
                        color: "#f5f5f5",
                      }}
                    >
                      <div className="font-medium truncate">
                        {item.ticket_ids.join(", ")} — {item.account_name}
                      </div>
                      <div className="mt-0.5 leading-snug" style={{ color: "rgba(245,245,245,0.6)" }}>
                        {item.recommended_action}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      {snapshotTime && (
        <div
          className="px-4 py-2 shrink-0 text-xs"
          style={{
            borderTop: "1px solid rgba(255,255,255,0.05)",
            color: "rgba(245,245,245,0.35)",
          }}
        >
          Data as of: 2026-08-16 11:00 IST
        </div>
      )}
    </aside>
  );
}
