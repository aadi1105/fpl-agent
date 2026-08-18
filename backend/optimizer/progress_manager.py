import uuid
import time
import logging
import threading
from typing import Dict, Any, Optional

logger = logging.getLogger("progress_manager")

OPTIMIZATION_STAGES = [
    "LOADING_FPL_DATA",
    "LOADING_MODEL_ARTIFACTS",
    "GENERATING_PROJECTIONS",
    "CALCULATING_PLAYER_XP",
    "BUILDING_MILP_PROBLEM",
    "SOLVING_SQUAD_OPTIMIZATION",
    "SELECTING_STARTING_XI",
    "SELECTING_CAPTAIN_VICE",
    "COMPUTING_DIAGNOSTICS",
    "FINALIZING_RESULTS"
]

class JobProgressManager:
    """
    Thread-safe progress tracking and asynchronous background job store for MILP optimization jobs.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, mode: str) -> str:
        job_id = str(uuid.uuid4())
        now = time.time()
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "RUNNING",
                "mode": mode,
                "stage": OPTIMIZATION_STAGES[0],
                "stage_number": 1,
                "total_stages": len(OPTIMIZATION_STAGES),
                "progress_percent": 10,
                "message": "Loading FPL Data",
                "start_time": now,
                "elapsed_seconds": 0.0,
                "result": None,
                "error": None
            }
        return job_id

    def update_stage(self, job_id: str, stage_idx: int, message: str):
        with self._lock:
            if job_id in self._jobs:
                j = self._jobs[job_id]
                stage_num = stage_idx + 1
                j["stage"] = OPTIMIZATION_STAGES[stage_idx]
                j["stage_number"] = stage_num
                j["progress_percent"] = int((stage_num / len(OPTIMIZATION_STAGES)) * 100)
                j["message"] = message
                j["elapsed_seconds"] = round(time.time() - j["start_time"], 2)

    def complete_job(self, job_id: str, result: Dict[str, Any]):
        with self._lock:
            if job_id in self._jobs:
                j = self._jobs[job_id]
                j["status"] = "COMPLETED"
                j["stage"] = "FINALIZING_RESULTS"
                j["stage_number"] = len(OPTIMIZATION_STAGES)
                j["progress_percent"] = 100
                j["message"] = "Optimization Complete"
                j["elapsed_seconds"] = round(time.time() - j["start_time"], 2)
                j["result"] = result

    def fail_job(self, job_id: str, error_msg: str):
        with self._lock:
            if job_id in self._jobs:
                j = self._jobs[job_id]
                j["status"] = "FAILED"
                j["message"] = f"Optimization Failed: {error_msg}"
                j["error"] = error_msg
                j["elapsed_seconds"] = round(time.time() - j["start_time"], 2)

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if job_id not in self._jobs:
                return None
            j = self._jobs[job_id].copy()
            if j["status"] == "RUNNING":
                j["elapsed_seconds"] = round(time.time() - j["start_time"], 2)
            # Exclude full result payload from lightweight status endpoint
            j.pop("result", None)
            return j

    def get_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if job_id not in self._jobs:
                return None
            return self._jobs[job_id]

progress_manager = JobProgressManager()
