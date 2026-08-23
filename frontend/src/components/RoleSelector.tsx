/**
 * RoleSelector.tsx — Fixed dropdown to select the active mock session role.
 * No login form — just a selector that sets role + user_name for the session.
 * On change: parent must reset sessionId and clear messages.
 */

export type Role = "support_agent" | "csm";

export interface RoleOption {
  role: Role;
  userName: string;
  label: string;
}

export const ROLE_OPTIONS: RoleOption[] = [
  { role: "support_agent", userName: "Rohit",       label: "Rohit — Support Agent" },
  { role: "support_agent", userName: "Maya",        label: "Maya — Support Agent" },
  { role: "csm",           userName: "Priya Mehta", label: "Priya Mehta — CSM" },
];

interface RoleSelectorProps {
  currentLabel: string;
  onRoleChange: (role: Role, userName: string, label: string) => void;
}

export function RoleSelector({ currentLabel, onRoleChange }: RoleSelectorProps) {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const option = ROLE_OPTIONS.find((o) => o.label === e.target.value);
    if (option) {
      onRoleChange(option.role, option.userName, option.label);
    }
  };

  return (
    <select
      value={currentLabel}
      onChange={handleChange}
      className="rounded-md px-3 py-1.5 text-sm font-medium cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
      style={{
        background: "#1c1c1c",
        color: "#f5f5f5",
        border: "1px solid rgba(255,255,255,0.1)",
      }}
      aria-label="Select user role"
    >
      {ROLE_OPTIONS.map((o) => (
        <option key={o.label} value={o.label}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
