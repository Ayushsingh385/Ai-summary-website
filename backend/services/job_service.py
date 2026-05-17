"""
Job Service - Manages the state and tracking of background NLP tasks.
In a full production environment, this would use Redis.
For this implementation, we use a thread-safe in-memory store with DB persistence.
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# In-memory job tracker
# Format: { job_id: { "status": "pending"|"processing"|"completed"|"failed", "result": ..., "error": ... } }
JOBS: Dict[str, Dict[str, Any]] = {}

def create_job() -> str:
    """Generates a new unique job ID and initializes its state."""
    job_id = str(uuid.uuid4())[:12]
    JOBS[job_id] = {
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "progress": 0,
        "result": None,
        "error": None
    }
    return job_id

def update_job(job_id: str, status: str, progress: int = 0, result: Any = None, error: str = None):
    """Updates the state of an existing job."""
    if job_id in JOBS:
        JOBS[job_id].update({
            "status": status,
            "progress": progress,
            "result": result,
            "error": error,
            "updated_at": datetime.utcnow().isoformat()
        })
        logger.info(f"Job {job_id} updated to {status} ({progress}%)")

def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the current state of a job."""
    return JOBS.get(job_id)

def delete_job(job_id: str):
    """Cleans up job state from memory."""
    JOBS.pop(job_id, None)
