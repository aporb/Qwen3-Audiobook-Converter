# Job Queue System Documentation

## Overview

VoxCraft now includes a comprehensive session-based job queue system that allows users to:
- Submit jobs that persist across page navigation
- Manage job chains with dependencies
- Pause, resume, and cancel jobs
- Track progress in real-time
- Prioritize and reorder jobs

## Architecture

### Backend Components

```
voxcraft/backend/
├── models/queue.py          # SQLAlchemy models (Job, JobStatus, JobType)
├── services/queue_service.py # Queue management service
├── utils/job_runner.py      # Async job executor with dependency resolution
├── routers/queue.py         # FastAPI endpoints
└── tasks/                   # Task handlers
    ├── tts_tasks.py
    ├── url_tasks.py
    ├── audiobook_tasks.py
    └── cleaning_tasks.py
```

### Frontend Components

```
voxcraft/frontend/src/
├── stores/useQueueStore.ts       # Zustand state management
├── lib/queueApi.ts               # API client
└── components/queue/
    ├── QueueBell.tsx            # Global notification bell
    ├── QueuePanel.tsx           # Slide-out job manager
    └── JobItem.tsx              # Individual job display
```

## Features

### 1. Session-Level Isolation
- Each user session has its own job queue
- Session ID managed server-side via headers
- Jobs persist across page navigation within same session

### 2. Job Types
- **TTS**: Text-to-speech conversion
- **URL_FETCH**: Fetch and extract web content
- **SUMMARIZE**: Generate summaries with insights
- **AUDIOBOOK**: Full audiobook conversion
- **CLEANING**: AI text cleaning
- **BATCH**: Batch processing

### 3. Job Chains
Submit dependent jobs that execute in sequence:
```python
# Example: URL → Summarize → TTS
steps = [
    {"type": "url_fetch", "payload": {"url": "..."}},
    {"type": "summarize", "payload": {"text": "{{job_1.result.content}}"}},
    {"type": "tts", "payload": {"text": "{{job_2.result.summary}}"}}
]
```

### 4. Priority Management
- Priority scale: 1-10 (1 = highest priority)
- Drag-drop reordering in UI (pending jobs only)
- Higher priority jobs execute first

### 5. Job Lifecycle
```
PENDING → RUNNING → COMPLETED
   ↓         ↓           
PAUSED    FAILED
   ↓         ↓
RESUMED  CANCELLED
```

### 6. Auto-Cleanup
- Jobs expire after 30 days
- Completed/failed jobs can be manually cleared
- Daily cleanup of expired jobs

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/queue/submit` | POST | Submit single job |
| `/api/queue/submit-chain` | POST | Submit job chain |
| `/api/queue/jobs` | GET | List jobs (with filters) |
| `/api/queue/jobs/{id}` | GET | Get job details |
| `/api/queue/jobs/{id}/cancel` | POST | Cancel job |
| `/api/queue/jobs/{id}/pause` | POST | Pause running job |
| `/api/queue/jobs/{id}/resume` | POST | Resume paused job |
| `/api/queue/jobs/{id}/priority` | POST | Update priority |
| `/api/queue/reorder` | POST | Reorder jobs |
| `/api/queue/stats` | GET | Get job statistics |
| `/api/queue/clear-completed` | POST | Clear completed jobs |

## UI Components

### QueueBell
- Located in header (next to settings)
- Shows count of active jobs (pending + running + paused)
- Click to open QueuePanel

### QueuePanel
- Slide-out drawer from right side
- Tabbed interface: Active | Paused | Completed | Failed
- Real-time updates (polls every 2 seconds)
- Job actions: Cancel, Pause, Resume, Delete
- Progress bars and status indicators

### JobItem
- Expandable job details
- Status icons and colors
- Progress percentage
- Dependency chain visualization
- Action buttons (context-aware)

## Usage Example

### Submit a Job
```typescript
import { submitJob } from "@/lib/queueApi";

const job = await submitJob("tts", {
  text: "Hello world",
  engine: "openai",
  voice: "alloy"
}, priority = 5);
```

### Submit a Chain
```typescript
import { submitChain } from "@/lib/queueApi";

const jobs = await submitChain([
  { type: "url_fetch", payload: { url: "https://example.com" } },
  { type: "summarize", payload: { text: "{{jobs[0].result.content}}" } },
  { type: "tts", payload: { text: "{{jobs[1].result.summary}}" } }
]);
```

### Track Progress
```typescript
import { useQueueStore } from "@/stores/useQueueStore";

const jobs = useQueueStore((s) => s.getActiveJobs());
// Auto-updates every 2 seconds via polling
```

## Database Schema

```sql
CREATE TABLE jobs (
    id VARCHAR(32) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL,
    job_type VARCHAR(20) NOT NULL,
    payload JSON,
    result JSON,
    error_message TEXT,
    dependencies JSON,
    parent_job_id VARCHAR(32),
    priority INTEGER DEFAULT 5,
    progress FLOAT DEFAULT 0.0,
    progress_message VARCHAR(255),
    created_at DATETIME,
    updated_at DATETIME,
    expires_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME
);
```

## Next Steps / Future Enhancements

1. **SSE Streaming**: Replace polling with Server-Sent Events for real-time updates
2. **Job Retry**: Add automatic retry logic for failed jobs
3. **Batch Operations**: Select and cancel multiple jobs at once
4. **Job History**: Persist job history across sessions (if user logs in)
5. **Performance**: Add pagination for large job lists
6. **Notifications**: Browser notifications when jobs complete

## Troubleshooting

### Jobs not appearing
- Check session ID is being sent in headers
- Verify backend is running and database is initialized
- Check browser console for API errors

### Dependencies not resolving
- Ensure dependency job IDs are valid
- Check dependency job completed successfully
- Verify template syntax: `{{job_id.result.field}}`

### Performance issues
- Large result payloads can slow down polling
- Consider implementing pagination for job lists
- Use SSE instead of polling for high-frequency updates