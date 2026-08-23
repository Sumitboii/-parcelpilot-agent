/**
 * ToolChip.tsx — Inline pill badge shown in the chat stream when the agent invokes a tool.
 * Rendered BEFORE the final answer arrives so the user sees tool usage in real-time.
 */

interface ToolChipProps {
  tool: string;
}

const TOOL_CONFIG: Record<string, { icon: string; label: string }> = {
  document_search: { icon: "🔍", label: "document_search" },
  data_lookup:     { icon: "📊", label: "data_lookup" },
  escalate:        { icon: "⚡", label: "escalate" },
};

export function ToolChip({ tool }: ToolChipProps) {
  const config = TOOL_CONFIG[tool] ?? { icon: "🔧", label: tool };

  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-mono animate-fade-in"
      style={{
        background: "rgba(37,99,235,0.15)",
        color: "#2563eb",
        border: "1px solid rgba(37,99,235,0.3)",
      }}
    >
      {config.icon} {config.label}
    </span>
  );
}
