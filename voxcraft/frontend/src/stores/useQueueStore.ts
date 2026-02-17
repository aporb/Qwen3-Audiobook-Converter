import { create } from "zustand";
import { persist } from "zustand/middleware";

export type JobStatus = "pending" | "running" | "paused" | "completed" | "failed" | "cancelled";
export type JobType = "tts" | "url_fetch" | "summarize" | "audiobook" | "cleaning" | "batch";

export interface Job {
  id: string;
  session_id: string;
  status: JobStatus;
  job_type: JobType;
  payload: Record<string, unknown>;
  result?: Record<string, unknown>;
  error_message?: string;
  dependencies: string[];
  parent_job_id?: string;
  priority: number;
  progress: number;
  progress_message: string;
  created_at: string;
  updated_at?: string;
  expires_at?: string;
  started_at?: string;
  completed_at?: string;
}

export interface JobStats {
  pending: number;
  running: number;
  paused: number;
  completed: number;
  failed: number;
  cancelled: number;
  total_active: number;
}

interface QueueState {
  // Jobs
  jobs: Job[];
  selectedJobId: string | null;
  isLoading: boolean;
  error: string | null;
  
  // UI State
  isPanelOpen: boolean;
  activeTab: "active" | "paused" | "completed" | "failed";
  
  // Session
  sessionId: string;
  
  // Actions
  setJobs: (jobs: Job[]) => void;
  addJob: (job: Job) => void;
  updateJob: (jobId: string, updates: Partial<Job>) => void;
  removeJob: (jobId: string) => void;
  setSelectedJob: (jobId: string | null) => void;
  setPanelOpen: (open: boolean) => void;
  setActiveTab: (tab: "active" | "paused" | "completed" | "failed") => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setSessionId: (sessionId: string) => void;
  
  // Computed
  getActiveJobs: () => Job[];
  getPausedJobs: () => Job[];
  getCompletedJobs: () => Job[];
  getFailedJobs: () => Job[];
  getJobById: (id: string) => Job | undefined;
  getTotalActiveCount: () => number;
}

const generateSessionId = () => {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
};

export const useQueueStore = create<QueueState>()(
  persist(
    (set, get) => ({
      // Initial state
      jobs: [],
      selectedJobId: null,
      isLoading: false,
      error: null,
      isPanelOpen: false,
      activeTab: "active",
      sessionId: generateSessionId(),

      // Actions
      setJobs: (jobs) => set({ jobs }),
      
      addJob: (job) => set((state) => ({ 
        jobs: [job, ...state.jobs] 
      })),
      
      updateJob: (jobId, updates) => set((state) => ({
        jobs: state.jobs.map((job) =>
          job.id === jobId ? { ...job, ...updates } : job
        ),
      })),
      
      removeJob: (jobId) => set((state) => ({
        jobs: state.jobs.filter((job) => job.id !== jobId),
        selectedJobId: state.selectedJobId === jobId ? null : state.selectedJobId,
      })),
      
      setSelectedJob: (jobId) => set({ selectedJobId: jobId }),
      setPanelOpen: (open) => set({ isPanelOpen: open }),
      setActiveTab: (tab) => set({ activeTab: tab }),
      setLoading: (loading) => set({ isLoading: loading }),
      setError: (error) => set({ error }),
      setSessionId: (sessionId) => set({ sessionId }),

      // Computed
      getActiveJobs: () => {
        const { jobs } = get();
        return jobs.filter((job) => ["pending", "running"].includes(job.status));
      },
      
      getPausedJobs: () => {
        const { jobs } = get();
        return jobs.filter((job) => job.status === "paused");
      },
      
      getCompletedJobs: () => {
        const { jobs } = get();
        return jobs.filter((job) => job.status === "completed");
      },
      
      getFailedJobs: () => {
        const { jobs } = get();
        return jobs.filter((job) => ["failed", "cancelled"].includes(job.status));
      },
      
      getJobById: (id) => {
        const { jobs } = get();
        return jobs.find((job) => job.id === id);
      },
      
      getTotalActiveCount: () => {
        const { jobs } = get();
        return jobs.filter((job) => ["pending", "running", "paused"].includes(job.status)).length;
      },
    }),
    {
      name: "voxcraft-queue",
      partialize: (state) => ({ 
        sessionId: state.sessionId,
        // Don't persist jobs - they should be fetched fresh
      }),
    }
  )
);