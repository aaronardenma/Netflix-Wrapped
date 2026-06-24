import hashlib
import io
import json
from contextlib import nullcontext
from datetime import timedelta

import pandas as pd
from django.core.cache import cache
from django.utils import timezone


ANONYMOUS_CACHE_TTL_SECONDS = 60 * 60 * 24
ANONYMOUS_CSV_TTL_SECONDS = 60 * 60 * 24
RECENT_PROCESSING_JOBS_CACHE_KEY = "recent_processing_jobs"
RECENT_PROCESSING_JOB_LIMIT = 25
USABLE_YEAR_STATUSES = {"ready", "partial_ready"}


def owner_key(user, job_id):
    return f"user:{user.id}" if user else f"anonymous:{job_id}"


def upload_cache_key(owner, job_id):
    return f"csv_data_{owner}_{job_id}"


def result_cache_key(owner, profile_name, year):
    profile_hash = hashlib.sha256(
        str(profile_name).encode("utf-8")
    ).hexdigest()[:16]
    year_key = "all" if str(year).lower() == "all" else str(int(year))
    return f"processed_data_{owner}_{profile_hash}_{year_key}"


def processing_state_key(job_id):
    return f"processing_state_{job_id}"


def job_status_key(job_id):
    return f"job_status_{job_id}"


def anonymous_expiry():
    return timezone.now() + timedelta(seconds=ANONYMOUS_CACHE_TTL_SECONDS)


def create_processing_state(
    profile_years,
    status_value="queued",
    expires_at=None,
):
    profiles = {
        profile_name: {
            str(year): status_value for year in sorted(years, reverse=True)
        }
        for profile_name, years in profile_years.items()
    }
    total = sum(len(years) for years in profile_years.values())
    processed = total if status_value == "ready" else 0
    return {
        "status": "running",
        "profile_years": {
            profile_name: sorted(years, reverse=True)
            for profile_name, years in profile_years.items()
        },
        "profiles": profiles,
        "selected_profile": None,
        "total": total,
        "processed": processed,
        "failed": 0,
        "percent": 100 if total == 0 or status_value == "ready" else 0,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "worker_started_at": None,
        "worker_finished_at": None,
    }


def get_processing_state(job_id):
    return cache.get(processing_state_key(job_id))


def set_processing_state(
    job_id,
    state,
    timeout=ANONYMOUS_CACHE_TTL_SECONDS,
):
    cache.set(processing_state_key(job_id), state, timeout=timeout)
    remember_processing_job(job_id)


def remember_processing_job(job_id):
    recent_jobs = cache.get(RECENT_PROCESSING_JOBS_CACHE_KEY) or []
    recent_jobs = [job for job in recent_jobs if job != job_id]
    recent_jobs.insert(0, job_id)
    cache.set(
        RECENT_PROCESSING_JOBS_CACHE_KEY,
        recent_jobs[:RECENT_PROCESSING_JOB_LIMIT],
        timeout=ANONYMOUS_CACHE_TTL_SECONDS,
    )


def recent_processing_jobs(limit=10):
    job_ids = (cache.get(RECENT_PROCESSING_JOBS_CACHE_KEY) or [])[:limit]
    jobs = []
    for job_id in job_ids:
        state = get_processing_state(job_id)
        if state:
            jobs.append(processing_status_payload(job_id, state))
            continue

        cached_status = cache.get(job_status_key(job_id))
        if cached_status == "completed":
            jobs.append(
                processing_status_payload(
                    job_id,
                    {"percent": 100},
                    status_value="completed",
                )
            )
        elif isinstance(cached_status, str) and cached_status.startswith("error:"):
            jobs.append(
                processing_status_payload(
                    job_id,
                    status_value="error",
                    error=cached_status[6:],
                )
            )
    return jobs


def update_processing_state(
    job_id,
    profile_name=None,
    year=None,
    year_status=None,
    job_status=None,
    selected_profile=None,
    worker_started_at=None,
    worker_finished_at=None,
):
    lock_factory = getattr(cache, "lock", None)
    lock = (
        lock_factory(
            f"processing-state-lock:{job_id}",
            timeout=30,
            blocking_timeout=5,
        )
        if lock_factory
        else nullcontext()
    )
    with lock:
        state = get_processing_state(job_id) or {}
        if job_status:
            state["status"] = job_status
        if selected_profile is not None:
            state["selected_profile"] = selected_profile
        if worker_started_at is not None:
            state["worker_started_at"] = worker_started_at
        if worker_finished_at is not None:
            state["worker_finished_at"] = worker_finished_at
        if profile_name is not None and year is not None and year_status:
            profile_state = state.setdefault("profiles", {}).setdefault(
                profile_name,
                {},
            )
            previous_status = profile_state.get(str(year))
            profile_state[str(year)] = year_status
            if (
                previous_status not in {"ready", "partial_ready", "error"}
                and year_status in {"ready", "error"}
            ):
                counter = "processed" if year_status == "ready" else "failed"
                state[counter] = int(state.get(counter, 0)) + 1

            total = int(state.get("total", 0) or 0)
            completed = int(state.get("processed", 0)) + int(
                state.get("failed", 0)
            )
            state["percent"] = (
                round((completed / total) * 100) if total else 100
            )

        set_processing_state(job_id, state)
        return state


def ready_profile_years(state):
    ready = {}
    for profile_name, years in (state or {}).get("profiles", {}).items():
        completed_years = [
            int(year)
            for year, year_status in years.items()
            if year_status in USABLE_YEAR_STATUSES
        ]
        if completed_years:
            ready[profile_name] = sorted(completed_years, reverse=True)
    return ready


def processing_status_payload(
    job_id,
    processing_state=None,
    *,
    status_value=None,
    message=None,
    error=None,
):
    state = processing_state or {}
    payload = {
        "status": status_value or state.get("status", "running"),
        "job_id": job_id,
        "profile_years": state.get("profile_years", {}),
        "profiles": state.get("profiles", {}),
        "ready_profile_years": ready_profile_years(state),
        "selected_profile": state.get("selected_profile"),
        "total": state.get("total", 0),
        "processed": state.get("processed", 0),
        "failed": state.get("failed", 0),
        "percent": state.get("percent", 0),
        "expires_at": state.get("expires_at"),
        "worker_started_at": state.get("worker_started_at"),
        "worker_finished_at": state.get("worker_finished_at"),
    }
    if message:
        payload["message"] = message
    if error:
        payload["error"] = error
    return payload


def store_upload(owner, job_id, upload_data):
    cache.set(
        upload_cache_key(owner, job_id),
        json.dumps(upload_data),
        timeout=ANONYMOUS_CSV_TTL_SECONDS,
    )


def load_upload(owner, job_id):
    cached_upload = cache.get(upload_cache_key(owner, job_id))
    if not cached_upload:
        return None, None

    upload_data = json.loads(cached_upload)
    dataframe = pd.read_json(
        io.StringIO(upload_data["dataframe_json"]),
        orient="records",
    )
    return upload_data, dataframe
