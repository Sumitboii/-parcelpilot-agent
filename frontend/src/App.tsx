/**
 * App.tsx — Root application shell.
 * Layout: Header (logo + role selector) | Sidebar (ProactivePanel) | Main (ChatPanel)
 */
import { useState } from "react";
import { RoleSelector, ROLE_OPTIONS, type Role } from "./components/RoleSelector";
import { ProactivePanel } from "./components/ProactivePanel";
import { ChatPanel } from "./components/ChatPanel";

function generateSessionId(): string {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

export default function App() {
  const defaultRole = ROLE_OPTIONS[0];
  const [role, setRole] = useState<Role>(defaultRole.role);
  const [userName, setUserName] = useState(defaultRole.userName);
  const [roleLabel, setRoleLabel] = useState(defaultRole.label);
  const [sessionId, setSessionId] = useState(generateSessionId);
  const [autoSendQuery, setAutoSendQuery] = useState("");

  const handleRoleChange = (newRole: Role, newUserName: string, newLabel: string) => {
    setRole(newRole);
    setUserName(newUserName);
    setRoleLabel(newLabel);
    setSessionId(generateSessionId());
    setAutoSendQuery("");
  };

  return (
    <div className="flex flex-col h-screen" style={{ background: "#0a0a0a", color: "#f5f5f5" }}>
      {/* Header */}
      <header
        className="shrink-0 flex items-center justify-between px-5 h-14"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", background: "#0a0a0a" }}
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold tracking-tight" style={{ color: "#f5f5f5" }}>
            ParcelPilot
          </span>
          <span className="text-xs" style={{ color: "rgba(245,245,245,0.35)" }}>
            Internal Support
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Active role badge */}
          <span className="text-xs" style={{ color: "rgba(245,245,245,0.5)" }}>
            {roleLabel}
          </span>
          <RoleSelector currentLabel={roleLabel} onRoleChange={handleRoleChange} />
        </div>
      </header>

      {/* Body: sidebar + main */}
      <div className="flex flex-1 min-h-0">
        {/* Proactive sidebar */}
        <div className="shrink-0 w-80">
          <ProactivePanel onPrePopulate={setAutoSendQuery} />
        </div>

        {/* Chat main area — centered, max-width 780px */}
        <main className="flex-1 overflow-hidden">
          <div className="mx-auto h-full" style={{ maxWidth: 780 }}>
            <ChatPanel
              sessionId={sessionId}
              role={role}
              userName={userName}
              autoSendQuery={autoSendQuery}
              onClearAutoSend={() => setAutoSendQuery("")}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
