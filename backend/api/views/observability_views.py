from collections import Counter
from time import perf_counter

import django_rq
from django.core.cache import cache
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.services.recap_cache import recent_processing_jobs


def timed_check(check):
    start = perf_counter()
    try:
        details = check() or {}
        return {
            "status": "ok",
            "latency_ms": round((perf_counter() - start) * 1000, 2),
            **details,
        }
    except Exception as exc:
        return {
            "status": "error",
            "latency_ms": round((perf_counter() - start) * 1000, 2),
            "error": str(exc),
        }


def database_check():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return {}


def cache_check():
    key = "observability:healthcheck"
    cache.set(key, "ok", timeout=10)
    if cache.get(key) != "ok":
        raise RuntimeError("cache read/write check failed")
    return {}


def rq_check():
    queue = django_rq.get_queue("recaps")
    return {
        "queue": queue.name,
        "queued_jobs": queue.count,
    }


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        checks = {
            "database": timed_check(database_check),
            "cache": timed_check(cache_check),
            "rq": timed_check(rq_check),
        }
        recent_jobs = recent_processing_jobs()
        job_counts = Counter(job.get("status", "unknown") for job in recent_jobs)
        overall_status = (
            "ok"
            if all(check["status"] == "ok" for check in checks.values())
            else "degraded"
        )
        status_code = 200 if overall_status == "ok" else 503

        return Response(
            {
                "status": overall_status,
                "checks": checks,
                "recent_jobs": recent_jobs,
                "job_counts": dict(job_counts),
            },
            status=status_code,
        )
