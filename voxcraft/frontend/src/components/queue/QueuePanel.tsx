import { useEffect, useState, useCallback, useRef } from "react";
import { X, Trash2, RefreshCw, Activity, CheckCircle, AlertCircle, PauseCircle, GripVertical } from "lucide-react";
import { clsx } from "clsx";
import { useQueueStore, Job } from "@/stores/useQueueStore";
import { JobItem } from "./JobItem";
import { listJobs, getStats, clearCompleted, connectToSSE, reorderJobs } from "@/lib/queueApi";

export function QueuePanel() {
  const { 
    isPanelOpen, 
    setPanelOpen, 
    activeTab, 
    setActiveTab,
    jobs,
    setJobs,
    updateJob,
    addJob,
    getActiveJobs,
    getPausedJobs,
    getCompletedJobs,
    getFailedJobs,
    reorderJobs: reorderJobsInStore,
  } = useQueueStore();
  
  const [stats, setStats] = useState({
    pending: 0,
    running: 0,
    paused: 0,
    completed: 0,
    failed: 0,
    cancelled: 0,
    total_active: 0,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [isClearing, setIsClearing] = useState(false);
  const [draggedJobId, setDraggedJobId] = useState<string | null>(null);
  const [dragOverJobId, setDragOverJobId] = useState<string | null>(null);
  const disconnectRef = useRef<(() => void) | null>(null);

  const fetchJobs = useCallback(async () => {
    if (!isPanelOpen) return;
    
    setIsLoading(true);
    try {
      let status: string | undefined;
      switch (activeTab) {
        case "active":
          status = undefined;
          break;
        case "paused":
          status = "paused";
          break;
        case "completed":
          status = "completed";
          break;
        case "failed":
          status = undefined;
          break;
      }
      
      const data = await listJobs(status, undefined, 100);
      setJobs(data.jobs);
      
      const statsData = await getStats();
      setStats(statsData);
    } catch (error) {
      console.error("Failed to fetch jobs:", error);
    } finally {
      setIsLoading(false);
    }
  }, [isPanelOpen, activeTab, setJobs]);

  // Initial fetch when panel opens
  useEffect(() => {
    if (isPanelOpen) {
      fetchJobs();
    }
  }, [isPanelOpen, fetchJobs]);

  // SSE Connection for real-time updates
  useEffect(() => {
    if (!isPanelOpen) {
      // Disconnect SSE when panel closes
      if (disconnectRef.current) {
        disconnectRef.current();
        disconnectRef.current = null;
      }
      return;
    }

    // Connect to SSE
    const disconnect = connectToSSE((event, data) => {
      switch (event) {
        case "job_created":
          addJob(data as Job);
          break;
        case "job_update":
          updateJob((data as Job).id, data as Partial<Job>);
          break;
        case "job_completed":
          updateJob((data as Job).id, { status: "completed", progress: 1, result: (data as Job).result });
          break;
        case "job_failed":
          const failedData = data as { job_id: string; error: string };
          updateJob(failedData.job_id, { status: "failed", error_message: failedData.error });
          break;
        case "stats_update":
          setStats(data as typeof stats);
          break;
      }
    });

    disconnectRef.current = disconnect;

    return () => {
      if (disconnectRef.current) {
        disconnectRef.current();
        disconnectRef.current = null;
      }
    };
  }, [isPanelOpen, addJob, updateJob]);

  const handleClearCompleted = async () => {
    setIsClearing(true);
    try {
      await clearCompleted();
      await fetchJobs();
    } catch (error) {
      console.error("Failed to clear completed jobs:", error);
    } finally {
      setIsClearing(false);
    }
  };

  const getFilteredJobs = (): Job[] => {
    switch (activeTab) {
      case "active":
        return getActiveJobs();
      case "paused":
        return getPausedJobs();
      case "completed":
        return getCompletedJobs();
      case "failed":
        return getFailedJobs();
      default:
        return jobs;
    }
  };

  const filteredJobs = getFilteredJobs();

  // Drag and Drop Handlers
  const handleDragStart = (e: React.DragEvent, jobId: string) => {
    if (activeTab !== "active") return; // Only allow reordering in active tab
    setDraggedJobId(jobId);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent, jobId: string) => {
    e.preventDefault();
    if (activeTab !== "active" || draggedJobId === jobId) return;
    setDragOverJobId(jobId);
  };

  const handleDragLeave = () => {
    setDragOverJobId(null);
  };

  const handleDrop = async (e: React.DragEvent, targetJobId: string) => {
    e.preventDefault();
    setDragOverJobId(null);
    
    if (!draggedJobId || draggedJobId === targetJobId || activeTab !== "active") {
      setDraggedJobId(null);
      return;
    }

    // Reorder jobs
    const currentOrder = getActiveJobs().map(j => j.id);
    const draggedIndex = currentOrder.indexOf(draggedJobId);
    const targetIndex = currentOrder.indexOf(targetJobId);

    if (draggedIndex === -1 || targetIndex === -1) {
      setDraggedJobId(null);
      return;
    }

    // Create new order
    const newOrder = [...currentOrder];
    newOrder.splice(draggedIndex, 1);
    newOrder.splice(targetIndex, 0, draggedJobId);

    // Update local state optimistically
    reorderJobsInStore(newOrder);

    // Update priorities on server
    try {
      await reorderJobs(newOrder);
    } catch (error) {
      console.error("Failed to reorder jobs:", error);
      // Revert on error
      fetchJobs();
    }

    setDraggedJobId(null);
  };

  const tabs = [
    { id: "active" as const, label: "Active", count: stats.pending + stats.running, icon: Activity },
    { id: "paused" as const, label: "Paused", count: stats.paused, icon: PauseCircle },
    { id: "completed" as const, label: "Completed", count: stats.completed, icon: CheckCircle },
    { id: "failed" as const, label: "Failed", count: stats.failed + stats.cancelled, icon: AlertCircle },
  ];

  if (!isPanelOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={() => setPanelOpen(false)}
      />
      
      {/* Panel */}
      <div className="relative w-full max-w-lg h-full bg-surface border-l border-glass-border shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-glass-border">
          <div>
            <h2 className="text-lg font-semibold text-text-primary">Job Queue</h2>
            <p className="text-xs text-text-secondary">
              {stats.total_active > 0 
                ? `${stats.total_active} active job${stats.total_active !== 1 ? 's' : ''}`
                : 'No active jobs'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchJobs}
              disabled={isLoading}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw className={clsx("w-4 h-4 text-text-secondary", isLoading && "animate-spin")} />
            </button>
            <button
              onClick={() => setPanelOpen(false)}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
            >
              <X className="w-5 h-5 text-text-secondary" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-glass-border">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  "flex-1 flex items-center justify-center gap-1.5 py-3 text-sm font-medium transition-colors border-b-2",
                  activeTab === tab.id
                    ? "text-text-primary border-text-primary bg-white/5"
                    : "text-text-secondary border-transparent hover:text-text-primary hover:bg-white/5"
                )}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{tab.label}</span>
                {tab.count > 0 && (
                  <span className="ml-1 text-xs bg-surface px-1.5 py-0.5 rounded-full">
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Actions Bar */}
        {activeTab === "completed" && stats.completed > 0 && (
          <div className="px-4 py-2 border-b border-glass-border bg-surface/50">
            <button
              onClick={handleClearCompleted}
              disabled={isClearing}
              className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear completed jobs
            </button>
          </div>
        )}

        {/* Job List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {isLoading && jobs.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-text-secondary">
              <RefreshCw className="w-5 h-5 animate-spin mr-2" />
              Loading jobs...
            </div>
          ) : filteredJobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-text-secondary">
              <div className="w-12 h-12 rounded-full bg-surface flex items-center justify-center mb-2">
                {activeTab === "active" && <Activity className="w-6 h-6" />}
                {activeTab === "paused" && <PauseCircle className="w-6 h-6" />}
                {activeTab === "completed" && <CheckCircle className="w-6 h-6" />}
                {activeTab === "failed" && <AlertCircle className="w-6 h-6" />}
              </div>
              <p className="text-sm">No {activeTab} jobs</p>
            </div>
          ) : (
            filteredJobs.map((job) => (
              <div
                key={job.id}
                draggable={activeTab === "active" && job.status === "pending"}
                onDragStart={(e) => handleDragStart(e, job.id)}
                onDragOver={(e) => handleDragOver(e, job.id)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, job.id)}
                className={clsx(
                  "relative",
                  draggedJobId === job.id && "opacity-50",
                  dragOverJobId === job.id && "before:absolute before:inset-0 before:border-2 before:border-dashed before:border-blue-400 before:rounded-lg before:content-['']"
                )}
              >
                {activeTab === "active" && job.status === "pending" && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-6 cursor-move text-text-tertiary hover:text-text-secondary">
                    <GripVertical className="w-4 h-4" />
                  </div>
                )}
                <JobItem
                  job={job}
                  isExpanded={expandedJobId === job.id}
                  onToggleExpand={() => 
                    setExpandedJobId(expandedJobId === job.id ? null : job.id)
                  }
                />
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-glass-border text-xs text-text-tertiary text-center">
          Jobs auto-expire after 30 days • Drag pending jobs to reorder
        </div>
      </div>
    </div>
  );
}