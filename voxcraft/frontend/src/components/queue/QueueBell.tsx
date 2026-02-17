import { Bell } from "lucide-react";
import { useQueueStore } from "@/stores/useQueueStore";

export function QueueBell() {
  const { isPanelOpen, setPanelOpen, getTotalActiveCount } = useQueueStore();
  const activeCount = getTotalActiveCount();

  return (
    <button
      onClick={() => setPanelOpen(!isPanelOpen)}
      className="relative p-2 rounded-lg hover:bg-white/10 transition-colors"
      aria-label="Toggle job queue"
    >
      <Bell className="w-5 h-5 text-text-primary" />
      {activeCount > 0 && (
        <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 flex items-center justify-center bg-red-500 text-white text-xs font-bold rounded-full">
          {activeCount > 99 ? "99+" : activeCount}
        </span>
      )}
    </button>
  );
}