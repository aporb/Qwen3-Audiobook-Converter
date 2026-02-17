import { NavLink } from "react-router-dom";
import { clsx } from "clsx";
import { Badge } from "@/components/shared/Badge";
import { QueueBell } from "@/components/queue/QueueBell";
import { useEngineStore } from "@/stores/useEngineStore";
import { useUIStore } from "@/stores/useUIStore";

const navItems = [
  { to: "/", label: "Quick Clip" },
  { to: "/url-reader", label: "URL Reader" },
  { to: "/studio", label: "Studio" },
  { to: "/audiobook", label: "Audiobook" },
];

export function Header() {
  const engine = useEngineStore((s) => s.engine);
  const sidebarContext = useUIStore((s) => s.sidebarContext);
  const setSidebarContext = useUIStore((s) => s.setSidebarContext);
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);

  const handleSettingsClick = () => {
    if (sidebarContext === "settings" && sidebarOpen) {
      toggleSidebar();
    } else {
      setSidebarContext("settings");
      if (!sidebarOpen) toggleSidebar();
    }
  };

  return (
    <header className="h-14 flex items-center justify-between px-5 border-b border-glass-border bg-obsidian/80 backdrop-blur-lg z-30">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold text-white">
          VoxCraft
        </span>
        <Badge variant={engine === "mlx" ? "local" : "cloud"} dot>
          {engine === "mlx" ? "Privacy Mode" : "Studio Mode"}
        </Badge>
      </div>

      {/* Navigation */}
      <nav className="flex items-center gap-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              clsx(
                "px-3 py-1.5 text-sm font-medium rounded-lg transition-colors",
                isActive
                  ? "bg-white/10 text-white"
                  : "text-text-secondary hover:text-text-primary hover:bg-white/5",
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Queue & Settings */}
      <div className="w-32 flex justify-end items-center gap-2">
        <QueueBell />
        <button
          onClick={handleSettingsClick}
          className={clsx(
            "p-2 rounded-lg transition-colors",
            sidebarContext === "settings" && sidebarOpen
              ? "text-white bg-white/10"
              : "text-text-muted hover:text-text-secondary hover:bg-white/5",
          )}
          title="Settings"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
        </button>
      </div>
    </header>
  );
}
