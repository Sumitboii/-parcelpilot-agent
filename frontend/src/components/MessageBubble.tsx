/**
 * MessageBubble.tsx — Renders a single message in the chat stream.
 * Delegates tool_chip → ToolChip, confirmation → ConfirmationCard.
 */
import { ToolChip } from "./ToolChip";
import { ConfirmationCard, type PendingAction } from "./ConfirmationCard";

export type MessageType =
  | "user"
  | "assistant"
  | "tool_chip"
  | "confirmation"
  | "success"
  | "error";

export interface Message {
  id: string;
  type: MessageType;
  content: string | PendingAction;
  timestamp: Date;
}

interface MessageBubbleProps {
  message: Message;
  sessionId: string;
  onConfirmResult?: (result: "confirmed" | "cancelled", escalationId?: string) => void;
}

function escHtml(s: string) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function fmtInlineText(s: string) {
  // 1. Unicode brackets 【 ... 】 -> [ ... ]
  s = s.replace(/【(.*?)】/g, "[$1]");
  
  // 2. Structured data citations [table: key]
  s = s.replace(/\[(orders|accounts|tickets|credit_calc|sla_check):\s*([^\]]+)\]/gi, '<span class="cit" title="$1: $2">$1: $2</span>');
  
  // 3. Bracketed PDF citations [01_Support_Policy_v3_CURRENT.pdf, p.1]
  s = s.replace(/\[([a-zA-Z0-9_\-]+\.pdf[^\]]*)\]/gi, '<span class="cit" title="$1">$1</span>');
  
  // 4. Unbracketed PDF citations
  s = s.replace(/(?<!["'>\w])(\b\d{2}_[a-zA-Z0-9_\-]+\.pdf(?:,?\s*(?:p(?:age|\.)?\s*\d+|§\s*\d+[^,;\n<)]*))?)/gi, (match, cit) => {
    if (!cit || cit.includes("<span")) return match;
    return `<span class="cit" title="${cit.trim()}">${cit.trim()}</span>`;
  });

  // 5. Bold **text**
  s = s.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  
  // 6. Italic *text* or _text_
  s = s.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, "<em>$1</em>");
  
  // 7. Inline code `code`
  s = s.replace(/`([^`]+)`/g, '<code class="prose-code">$1</code>');
  
  // 8. Entity tags: TKT-505, ACCT-004, ORD-1001, KI-208
  s = s.replace(/\b(TKT-\d+|ACCT-\d+|ORD-\d+|KI-\d+)\b/g, '<span class="bg-neutral-800 text-neutral-200 border border-neutral-700 px-1.5 py-0.5 rounded text-[11px] font-mono">$1</span>');
  
  return s;
}

export function formatAgentContent(raw: string): string {
  if (!raw) return "";
  raw = raw.replace(/\u202f/g, " ").replace(/\u00a0/g, " ").replace(/\u2011/g, "-");
  const lines = raw.split(/\r?\n/);
  const out: string[] = [];
  
  let inTable = false;
  let tableRows: string[] = [];
  let inUl = false;
  let inOl = false;
  let inQuote = false;
  let quoteLines: string[] = [];
  
  function flushTable() {
    if (!inTable || tableRows.length === 0) { inTable = false; return; }
    let html = '<div class="overflow-x-auto my-2 rounded border border-neutral-800 bg-neutral-900/60"><table class="w-full text-xs text-left">';
    let bodyRows = tableRows;
    if (tableRows.length >= 2 && /^\s*\|?\s*[-:]+[-| :]*\|?\s*$/.test(tableRows[1])) {
      const headers = tableRows[0].replace(/^\||\|$/g, "").split("|").map(c => c.trim());
      html += '<thead class="bg-neutral-800/80 text-neutral-200"><tr>' + headers.map(h => `<th class="px-3 py-1.5 font-semibold">${fmtInlineText(escHtml(h))}</th>`).join("") + "</tr></thead>";
      bodyRows = tableRows.slice(2);
    }
    html += '<tbody class="divide-y divide-neutral-800 text-neutral-300">';
    for (const r of bodyRows) {
      const cells = r.replace(/^\||\|$/g, "").split("|").map(c => c.trim());
      html += "<tr>" + cells.map(c => `<td class="px-3 py-1.5">${fmtInlineText(escHtml(c))}</td>`).join("") + "</tr>";
    }
    html += "</tbody></table></div>";
    out.push(html);
    tableRows = [];
    inTable = false;
  }
  
  function flushList() {
    if (inUl) { out.push("</ul>"); inUl = false; }
    if (inOl) { out.push("</ol>"); inOl = false; }
  }
  
  function flushQuote() {
    if (inQuote) {
      out.push(`<blockquote class="border-l-2 border-blue-500 bg-blue-950/20 px-3 py-1.5 my-2 rounded text-xs text-neutral-300 italic">${fmtInlineText(escHtml(quoteLines.join(" ")))}</blockquote>`);
      inQuote = false;
      quoteLines = [];
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();
    
    if (/^[-*_]{3,}$/.test(trimmed)) {
      flushTable(); flushList(); flushQuote();
      out.push('<hr class="border-t border-neutral-800 my-3"/>');
      continue;
    }
    
    if (trimmed.includes("|") && (trimmed.startsWith("|") || /\w+\s*\|/.test(trimmed))) {
      flushList(); flushQuote();
      inTable = true;
      tableRows.push(trimmed);
      continue;
    } else if (inTable) {
      flushTable();
    }
    
    if (trimmed.startsWith(">")) {
      flushTable(); flushList();
      inQuote = true;
      quoteLines.push(trimmed.replace(/^>\s*/, ""));
      continue;
    } else if (inQuote) {
      flushQuote();
    }
    
    const hMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (hMatch) {
      flushTable(); flushList(); flushQuote();
      out.push(`<h4 class="font-semibold text-neutral-100 text-sm mt-3 mb-1">${fmtInlineText(escHtml(hMatch[2]))}</h4>`);
      continue;
    }
    
    const olMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (olMatch) {
      flushTable();
      if (inUl) flushList();
      if (!inOl) { out.push('<ol class="list-decimal ml-5 my-1.5 space-y-1 text-neutral-200">'); inOl = true; }
      out.push(`<li>${fmtInlineText(escHtml(olMatch[2]))}</li>`);
      continue;
    }
    
    const ulMatch = trimmed.match(/^[-*•]\s+(.*)$/);
    if (ulMatch) {
      flushTable();
      if (inOl) flushList();
      if (!inUl) { out.push('<ul class="list-disc ml-5 my-1.5 space-y-1 text-neutral-200">'); inUl = true; }
      out.push(`<li>${fmtInlineText(escHtml(ulMatch[1]))}</li>`);
      continue;
    }
    
    if (!trimmed) {
      flushTable(); flushList(); flushQuote();
      continue;
    }
    
    flushTable(); flushList(); flushQuote();
    out.push(`<p class="mb-2 leading-relaxed text-neutral-200">${fmtInlineText(escHtml(trimmed))}</p>`);
  }
  
  flushTable(); flushList(); flushQuote();
  return out.join("");
}

export function MessageBubble({ message, sessionId, onConfirmResult }: MessageBubbleProps) {
  const base = "animate-fade-in max-w-[680px]";

  if (message.type === "tool_chip") {
    return (
      <div className={`${base} py-0.5`}>
        <ToolChip tool={message.content as string} />
      </div>
    );
  }

  if (message.type === "confirmation") {
    return (
      <div className={`${base} w-full`}>
        <ConfirmationCard
          action={message.content as PendingAction}
          sessionId={sessionId}
          onResult={onConfirmResult ?? (() => {})}
        />
      </div>
    );
  }

  if (message.type === "user") {
    return (
      <div className={`${base} ml-auto`}>
        <div
          className="rounded-lg px-4 py-2.5 text-sm leading-relaxed"
          style={{ background: "#1c1c1c", color: "#f5f5f5" }}
        >
          {message.content as string}
        </div>
      </div>
    );
  }

  // assistant, success, error
  const borderColor =
    message.type === "success"
      ? "#22c55e"
      : message.type === "error"
      ? "#ef4444"
      : "transparent";

  const rawContent = typeof message.content === "string" ? message.content : "";
  const formattedHtml = formatAgentContent(rawContent);

  return (
    <div className={`${base}`}>
      <div
        className="rounded-lg px-4 py-2.5 text-sm leading-relaxed"
        style={{
          background: "#111111",
          color: "#f5f5f5",
          border: "1px solid rgba(255,255,255,0.05)",
          borderLeft: message.type !== "assistant" ? `4px solid ${borderColor}` : "1px solid rgba(255,255,255,0.05)",
        }}
        dangerouslySetInnerHTML={{ __html: formattedHtml }}
      />
    </div>
  );
}

