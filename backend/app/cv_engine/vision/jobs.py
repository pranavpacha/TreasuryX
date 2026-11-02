"""
In-process background job runner for long vision tasks (video analysis, optical-flow sequences).

Single-process, in-memory, bounded: jobs run on a small thread pool, report progress, can be
cancelled cooperatively (the worker calls ctx.check() between units of work) and fail
gracefully into a 'failed' state with the error text. Finished jobs are kept for a short time and
the store is capped, so memory cannot grow without bound. This is deliberately not a distributed
queue (no Celery/Redis): the app targets a single free-tier instance or a laptop.
"""
from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

MAX_JOBS = 40
TTL_SECONDS = 3600


class JobCancelled(Exception):
    pass


class JobContext:
    def __init__(self, job: dict):
        self._job = job

    def progress(self, fraction: float, message: str = ""):
        self._job["progress"] = round(float(min(1.0, max(0.0, fraction))), 3)
        if message:
            self._job["message"] = message

    def check(self):
        if self._job["cancel_requested"]:
            raise JobCancelled()


class JobStore:
    def __init__(self, workers: int = 2):
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="vision-job")
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def submit(self, kind: str, fn: Callable[[JobContext], Any], meta: dict | None = None) -> dict:
        job = {"id": uuid.uuid4().hex[:12], "kind": kind, "status": "queued", "progress": 0.0, "message": "queued", "result": None, "error": None,
               "cancel_requested": False, "created": time.time(), "finished": None, "meta": meta or {}, "persisted": False}
        with self._lock:
            self._gc()
            self._jobs[job["id"]] = job
        self._pool.submit(self._run, job, fn)
        return job

    def _run(self, job: dict, fn: Callable[[JobContext], Any]):
        if job["cancel_requested"]:
            job.update(status="cancelled", message="cancelled before start", finished=time.time())
            return
        job.update(status="running", message="running")
        try:
            job["result"] = fn(JobContext(job))
            job.update(status="done", progress=1.0, message="done")
        except JobCancelled:
            job.update(status="cancelled", message="cancelled")
        except Exception as exc:  # noqa: BLE001 -- surfaced to the client, not swallowed
            job.update(status="failed", error=f"{type(exc).__name__}: {exc}", message="failed")
        finally:
            job["finished"] = time.time()

    def get(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> dict | None:
        job = self._jobs.get(job_id)
        if job and job["status"] in ("queued", "running"):
            job["cancel_requested"] = True
            job["message"] = "cancel requested"
        return job

    def _gc(self):
        now = time.time()
        for jid in [j for j, v in self._jobs.items() if v["finished"] and now - v["finished"] > TTL_SECONDS]:
            self._jobs.pop(jid, None)
        while len(self._jobs) >= MAX_JOBS:
            done = [j for j, v in self._jobs.items() if v["finished"]]
            if not done:
                break
            self._jobs.pop(min(done, key=lambda j: self._jobs[j]["finished"]), None)

    @staticmethod
    def public(job: dict, include_result: bool = True) -> dict:
        out = {k: job[k] for k in ("id", "kind", "status", "progress", "message", "error", "created", "finished", "meta")}
        if include_result and job["status"] == "done":
            out["result"] = job["result"]
        return out


store = JobStore()
