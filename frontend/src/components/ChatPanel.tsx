/**
 * ChatPanel.tsx — Main chat interface with SSE streaming.
 * Fixed-height scrollable message list + pinned input bar.
 */
import { useEffect, useRef, useState } from "react";
import { streamSSE } from "../hooks/useSSE";
import { MessageBubble, type Message, type MessageType } from "./MessageBubble";
import type { PendingAction } from "./ConfirmationCard";

interface ChatPanelProps {
  sessionId: string;
  role: string;
  userName: string;
  prePopulatedInput: string;
  onClearPrePopulated: () => void;
}

export function ChatPanel({
  sessionId,
  role,
  userName,
  prePopulatedInput,
  onClearPrePopulated,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Apply pre-populated query from ProactivePanel
  useEffect(() => {
    if (prePopulatedInput) {
      setInput(prePopulatedInput);
      onClearPrePopulated();
      inputRef.current?.focus();
    }
  }, [prePopulatedInput, onClearPrePopulated]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  const addMessage = (type: MessageType, content: string | PendingAction) => {
    const msg: Message = {
      id: `${Date.now()}-${Math.random()}`,
      type,
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, msg]);
    return msg.id;
  };

  const updateLastAssistant = (text: string) => {
    setMessages((prev) => {
      const copy = [...prev];
      for (let i = copy.length - 1; i >= 0; i--) {
        if (copy[i].type === "assistant") {
          copy[i] = { ...copy[i], content: copy[i].content + text };
          return copy;
        }
      }
      // No assistant message yet — create one
      copy.push({ id: `${Date.now()}`, type: "assistant", content: text, timestamp: new Date() });
      return copy;
    });
  };

  const handleSubmit = async () => {
    const query = input.trim();
    if (!query || streaming) return;

    setInput("");
    setStreaming(true);
    addMessage("user", query);

    try {
      for await (const event of streamSSE("/chat", {
        message: query,
        session_id: sessionId,
        role,
        user_name: userName,
      })) {
        if (event.event === "tool_chip") {
          const d = event.data as { tool: string };
          addMessage("tool_chip", d.tool);
        } else if (event.event === "token") {
          const d = event.data as { text: string };
          updateLastAssistant(d.text);
        } else if (event.event === "pending_confirmation") {
          addMessage("confirmation", event.data as PendingAction);
        } else if (event.event === "error") {
          const d = event.data as { message: string };
          addMessage("error", d.message);
        } else if (event.event === "done") {
          break;
        }
      }
    } catch {
      addMessage("error", "Connection error. Please retry.");
    } finally {
      setStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleConfirmResult = (result: "confirmed" | "cancelled", escalationId?: string) => {
    if (result === "confirmed" && escalationId) {
      addMessage("success", `✓ Escalation created: ${escalationId}`);
    } else if (result === "cancelled") {
      addMessage("assistant", "Action cancelled.");
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Message list */}
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
        style={{ height: "calc(100vh - 180px)" }}
      >
        {messages.length === 0 && (
          <div className="h-full flex items-center justify-center">
            <p className="text-sm text-center" style={{ color: "rgba(245,245,245,0.3)" }}>
              Ask anything about ParcelPilot accounts, orders, tickets, or policies.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            sessionId={sessionId}
            onConfirmResult={handleConfirmResult}
          />
        ))}

        {/* Thinking indicator */}
        {streaming && (
          <div className="flex gap-1 py-1 animate-fade-in">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="rounded-full"
                style={{
                  width: 6,
                  height: 6,
                  background: "#2563eb",
                  opacity: 0.6,
                  animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Input bar */}
      <div
        className="shrink-0 px-4 py-3 flex gap-2 items-end"
        style={{ borderTop: "1px solid rgba(255,255,255,0.05)", background: "#0a0a0a" }}
      >
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={streaming}
          placeholder="Ask a question…"
          rows={1}
          className="flex-1 resize-none rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#2563eb] disabled:opacity-50"
          style={{
            background: "#111111",
            color: "#f5f5f5",
            border: "1px solid rgba(255,255,255,0.1)",
            maxHeight: 120,
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || streaming}
          className="rounded-lg px-4 py-2 text-sm font-semibold transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ background: "#2563eb", color: "#fff" }}
        >
          Send
        </button>
      </div>

      {/* Pulse animation for thinking dots */}
      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 0.4; }
          50% { transform: scale(1.4); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
