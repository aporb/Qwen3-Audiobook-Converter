import { useState } from "react";
import { 
  Play, 
  Pause, 
  Square, 
  Trash2, 
  ChevronDown, 
  ChevronUp,
  Link,
  Volume2,
  FileText,
  BookOpen,
  Sparkles,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { clsx } from "clsx";
import { Job, JobStatus, JobType } from "@/stores/useQueueStore";
import { cancelJob, pauseJob, resumeJob, deleteJob } from "@/lib/queueApi";
import { useQueueStore } from "@/stores/useQueueStore";

interface JobItemProps {
  job: Job;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

const statusIcons: Record<JobStatus, typeof Play> = {
  pending: Clock,
  running: Play,
  paused: Pause,
  completed: CheckCircle,
  failed: AlertCircle,
  cancelled: XCircle,
};

const statusColors: Record<JobStatus, string> = {
  pending: "text-text-secondary",
  running: "text-green-400",
  paused: "text-yellow-400",
  completed: "text-green-400",
  failed: "text-red-400",
  cancelled: "text-text-tertiary",
};

const jobTypeIcons: Record<JobType, typeof Volume2> = {
  tts: Volume2,
  url_fetch: Link,
  summarize: Sparkles,
  audiobook: BookOpen,
  cleaning: FileText,
  batch: BookOpen,
};

const jobTypeLabels: Record<JobType, string> = {
  tts: "Text to Speech",
  url_fetch: "Fetch URL",
  summarize: "Summarize",
  audiobook: "Audiobook",
  cleaning: "Clean Text",
  batch: "Batch Process",
};

export function JobItem({ job, isExpanded = false, onToggleExpand }: JobItemProps) {
  const [isLoading, setIsLoading] = useState(false);
  const { updateJob, removeJob } = useQueueStore();
  
  const StatusIcon = statusIcons[job.status];
  const TypeIcon = jobTypeIcons[job.job_type];
  const statusColor = statusColors[job.status];

  const handleCancel = async () => {
    setIsLoading(true);
    try {
      await cancelJob(job.id);
      updateJob(job.id, { status: "cancelled" });
    } catch (error) {
      console.error("Failed to cancel job:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePause = async () => {
    setIsLoading(true);
    try {
      await pauseJob(job.id);
      updateJob(job.id, { status: "paused" });
    } catch (error) {
      console.error("Failed to pause job:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResume = async () => {
    setIsLoading(true);
    try {
      await resumeJob(job.id);
      updateJob(job.id, { status: "pending" });
    } catch (error) {
      console.error("Failed to resume job:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    setIsLoading(true);
    try {
      await deleteJob(job.id);
      removeJob(job.id);
    } catch (error) {
      console.error("Failed to delete job:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const isTerminal = ["completed", "failed", "cancelled"].includes(job.status);
  const canCancel = ["pending", "running"].includes(job.status);
  const canPause = job.status === "running";
  const canResume = job.status === "paused";

  return (
    <div className="border border-glass-border rounded-lg overflow-hidden bg-surface/50">
      {/* Main Row */}
      <div 
        className="p-3 flex items-center gap-3 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={onToggleExpand}
      >
        {/* Status Icon */}
        <StatusIcon className={clsx("w-5 h-5 flex-shrink-0", statusColor)} />
        
        {/* Type Icon & Label */}
        <TypeIcon className="w-4 h-4 text-text-secondary flex-shrink-0" />
        <span className="text-sm text-text-secondary w-24 flex-shrink-0 hidden sm:block">
          {jobTypeLabels[job.job_type]}
        </span>
        
        {/* Job ID & Message */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-tertiary font-mono">{job.id.slice(0, 8)}</span>
            <span className="text-sm text-text-primary truncate">
              {job.progress_message || jobTypeLabels[job.job_type]}
            </span>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="w-24 flex-shrink-0 hidden sm:block">
          <div className="h-1.5 bg-surface rounded-full overflow-hidden">
            <div 
              className={clsx(
                "h-full transition-all duration-300",
                job.status === "failed" ? "bg-red-400" : 
                job.status === "completed" ? "bg-green-400" : "bg-blue-400"
              )}
              style={{ width: `${job.progress * 100}%` }}
            />
          </div>
          <div className="text-xs text-text-tertiary text-right mt-0.5">
            {Math.round(job.progress * 100)}%
          </div>
        </div>
        
        {/* Timestamp */}
        <span className="text-xs text-text-tertiary w-20 text-right flex-shrink-0 hidden md:block">
          {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}
        </span>
        
        {/* Expand/Collapse */}
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-text-tertiary flex-shrink-0" />
        ) : (
          <ChevronDown className="w-4 h-4 text-text-tertiary flex-shrink-0" />
        )}
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-glass-border bg-surface/30">
          {/* Progress Message */}
          {job.progress_message && (
            <div className="py-2 text-sm text-text-secondary">
              {job.progress_message}
            </div>
          )}
          
          {/* Error Message */}
          {job.error_message && (
            <div className="py-2 text-sm text-red-400 bg-red-500/10 rounded px-2 my-2">
              {job.error_message}
            </div>
          )}
          
          {/* Result */}
          {job.result && (
            <div className="py-2">
              <div className="text-xs text-text-tertiary mb-1">Result:</div>
              <pre className="text-xs text-text-secondary bg-surface rounded p-2 overflow-auto max-h-32">
                {JSON.stringify(job.result, null, 2)}
              </pre>
            </div>
          )}
          
          {/* Mobile Progress */}
          <div className="sm:hidden py-2">
            <div className="h-2 bg-surface rounded-full overflow-hidden">
              <div 
                className={clsx(
                  "h-full transition-all duration-300",
                  job.status === "failed" ? "bg-red-400" : 
                  job.status === "completed" ? "bg-green-400" : "bg-blue-400"
                )}
                style={{ width: `${job.progress * 100}%` }}
              />
            </div>
            <div className="text-xs text-text-tertiary text-right mt-1">
              {Math.round(job.progress * 100)}%
            </div>
          </div>
          
          {/* Action Buttons */}
          <div className="flex items-center gap-2 pt-2">
            {canCancel && (
              <button
                onClick={(e) => { e.stopPropagation(); handleCancel(); }}
                disabled={isLoading}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition-colors disabled:opacity-50"
              >
                <Square className="w-3 h-3" />
                Cancel
              </button>
            )}
            
            {canPause && (
              <button
                onClick={(e) => { e.stopPropagation(); handlePause(); }}
                disabled={isLoading}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-yellow-500/20 text-yellow-400 rounded hover:bg-yellow-500/30 transition-colors disabled:opacity-50"
              >
                <Pause className="w-3 h-3" />
                Pause
              </button>
            )}
            
            {canResume && (
              <button
                onClick={(e) => { e.stopPropagation(); handleResume(); }}
                disabled={isLoading}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-green-500/20 text-green-400 rounded hover:bg-green-500/30 transition-colors disabled:opacity-50"
              >
                <Play className="w-3 h-3" />
                Resume
              </button>
            )}
            
            {isTerminal && (
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(); }}
                disabled={isLoading}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-text-tertiary/20 text-text-tertiary rounded hover:bg-text-tertiary/30 transition-colors disabled:opacity-50"
              >
                <Trash2 className="w-3 h-3" />
                Delete
              </button>
            )}
            
            {/* Priority Badge */}
            <div className="ml-auto flex items-center gap-1 text-xs text-text-tertiary">
              <span>Priority:</span>
              <span className="font-mono bg-surface px-1.5 py-0.5 rounded">{job.priority}</span>
            </div>
          </div>
          
          {/* Dependencies */}
          {job.dependencies.length > 0 && (
            <div className="mt-2 pt-2 border-t border-glass-border">
              <div className="text-xs text-text-tertiary mb-1">Dependencies:</div>
              <div className="flex flex-wrap gap-1">
                {job.dependencies.map((depId) => (
                  <span 
                    key={depId} 
                    className="text-xs bg-surface px-2 py-0.5 rounded font-mono text-text-secondary"
                  >
                    {depId.slice(0, 8)}...
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}