# Music Generation Progress Tracking API

## Overview
API endpoints cho phép generate music activity với khả năng theo dõi progress real-time.

## Endpoints

### 1. Generate Dance Plan (Async)
**POST** `/music/generate-dance-plan`

Tạo dance plan bất đồng bộ, trả về task_id để tracking.

#### Request Body
```json
{
  "music_name": "My Song",
  "music_url": "https://example.com/song.mp3",
  "duration": 120.5,
  "robot_model_id": "uuid-here"
}
```

#### Response
```json
{
  "task_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "message": "Task created. Use GET /music/task/{task_id} to check progress."
}
```

---

### 2. Upload Music and Generate Plan (Async/Sync)
**POST** `/music/upload-music-and-generate-plan`

Upload file nhạc và generate plan. Hỗ trợ cả sync và async mode.

#### Request (multipart/form-data)
```
file: [MP3/MP4 file]
start_time: 0 (optional)
end_time: 30 (optional)
robot_model_id: "uuid-here"
async_mode: true (default: true)
```

#### Response (async_mode=true)
```json
{
  "task_id": "task-uuid",
  "message": "Task created. Use GET /music/task/{task_id} to check progress.",
  "music_info": {
    "name": "uploaded_song.mp3",
    "url": "https://storage.example.com/...",
    "duration": 30.0
  }
}
```

#### Response (async_mode=false)
```json
{
  "music_info": {
    "name": "song name",
    "music_file_url": "https://...",
    "duration": 120.5
  },
  "activity": {
    "actions": [...]
  },
  "robot_model_id": "uuid"
}
```

---

### 3. Check Task Progress
**GET** `/music/task/{task_id}`

Kiểm tra progress và status của task.

#### Response - Processing
```json
{
  "task_id": "task-uuid",
  "status": "processing",
  "progress": 40,
  "stage": "analyzing",
  "message": "Analyzing beats and energy...",
  "created_at": "2025-12-14T10:30:00Z",
  "updated_at": "2025-12-14T10:30:05Z"
}
```

#### Response - Completed
```json
{
  "task_id": "task-uuid",
  "status": "completed",
  "progress": 100,
  "stage": "completed",
  "message": "Activity generated successfully!",
  "result": {
    "music_info": {...},
    "activity": {...},
    "robot_model_id": "uuid"
  },
  "completed_at": "2025-12-14T10:30:15Z",
  "updated_at": "2025-12-14T10:30:15Z"
}
```

#### Response - Failed
```json
{
  "task_id": "task-uuid",
  "status": "failed",
  "progress": 0,
  "stage": "failed",
  "message": "Task failed",
  "error": "Connection timeout",
  "failed_at": "2025-12-14T10:30:10Z",
  "updated_at": "2025-12-14T10:30:10Z"
}
```

---

### 4. Delete Task
**DELETE** `/music/task/{task_id}`

Xóa task khỏi tracking system.

#### Response
```json
{
  "message": "Task deleted"
}
```

---

### 5. Generate Dance Plan (Sync - Legacy)
**POST** `/music/generate-dance-plan-sync`

Synchronous endpoint - blocks cho đến khi hoàn thành. Kept for backward compatibility.

---

## Progress Stages

| Stage | Progress | Description |
|-------|----------|-------------|
| `initializing` | 0% | Task được tạo |
| `loading` | 10% | Load robot configuration |
| `downloading` | 20% | Download file nhạc |
| `analyzing` | 40% | Phân tích beats và energy |
| `planning` | 60% | Generate dance choreography |
| `building` | 80% | Build activity JSON |
| `finalizing` | 95% | Hoàn thiện |
| `completed` | 100% | Hoàn thành thành công |
| `failed` | 0% | Lỗi xảy ra |

---

## Usage Examples

### JavaScript/TypeScript Frontend

```typescript
// 1. Start task
const response = await fetch('/music/generate-dance-plan', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    music_name: 'My Song',
    music_url: 'https://example.com/song.mp3',
    duration: 120.5,
    robot_model_id: 'robot-uuid'
  })
});

const { task_id } = await response.json();

// 2. Poll for progress
const pollInterval = setInterval(async () => {
  const statusRes = await fetch(`/music/task/${task_id}`);
  const status = await statusRes.json();
  
  console.log(`Progress: ${status.progress}% - ${status.message}`);
  
  if (status.status === 'completed') {
    clearInterval(pollInterval);
    console.log('Result:', status.result);
    // Use status.result for your application
  } else if (status.status === 'failed') {
    clearInterval(pollInterval);
    console.error('Failed:', status.error);
  }
}, 1000); // Poll every second
```

### React Hook Example

```typescript
function useMusicGeneration() {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  
  const generateMusic = async (musicData) => {
    setStatus('pending');
    
    // Start task
    const res = await fetch('/music/generate-dance-plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(musicData)
    });
    
    const { task_id } = await res.json();
    
    // Poll for updates
    const interval = setInterval(async () => {
      try {
        const statusRes = await fetch(`/music/task/${task_id}`);
        const taskStatus = await statusRes.json();
        
        setProgress(taskStatus.progress);
        setStatus(taskStatus.status);
        
        if (taskStatus.status === 'completed') {
          clearInterval(interval);
          setResult(taskStatus.result);
        } else if (taskStatus.status === 'failed') {
          clearInterval(interval);
          setError(taskStatus.error);
        }
      } catch (err) {
        clearInterval(interval);
        setError(err.message);
      }
    }, 1000);
  };
  
  return { progress, status, result, error, generateMusic };
}
```

### Python Client

```python
import requests
import time

def generate_music_with_progress(music_data):
    # Start task
    response = requests.post(
        'http://api.example.com/music/generate-dance-plan',
        json=music_data
    )
    task_id = response.json()['task_id']
    
    # Poll for progress
    while True:
        status_response = requests.get(
            f'http://api.example.com/music/task/{task_id}'
        )
        status = status_response.json()
        
        print(f"Progress: {status['progress']}% - {status['message']}")
        
        if status['status'] == 'completed':
            return status['result']
        elif status['status'] == 'failed':
            raise Exception(f"Task failed: {status['error']}")
        
        time.sleep(1)

# Usage
result = generate_music_with_progress({
    'music_name': 'My Song',
    'music_url': 'https://example.com/song.mp3',
    'duration': 120.5,
    'robot_model_id': 'robot-uuid'
})
```

---

## Technical Details

### Storage
- Progress data được lưu trong Redis
- TTL: 1 hour cho pending/processing tasks
- TTL: 2 hours cho completed tasks
- Task tự động expire sau TTL

### Performance
- Background tasks không block API response
- Client có thể poll với interval tùy ý (recommend: 1-2 seconds)
- Multiple concurrent tasks được support

### Error Handling
- Network errors khi download nhạc: Task failed
- Invalid robot_model_id: Task failed
- Redis connection error: Fallback to sync mode (in future)

---

## Migration from Sync to Async

Nếu bạn đang dùng endpoint sync cũ:

```typescript
// Old way (blocking)
const result = await fetch('/music/generate-dance-plan-sync', {...});

// New way (non-blocking with progress)
const { task_id } = await fetch('/music/generate-dance-plan', {...});
// Then poll /music/task/{task_id}
```

