import logging
from django.utils import timezone

import django_rq
from django.core.cache import cache

from api.services.recap_cache import (
    ANONYMOUS_CACHE_TTL_SECONDS,
    get_processing_state,
    job_status_key,
    load_upload,
    result_cache_key,
    update_processing_state,
)
from api.services.recap_data import (
    filter_profile_year,
    profile_comparisons_from_dataframe,
)
from api.services.recommendations import RecommendationError, generate_recommendations
from api.services.viewing_ingestion import ingest_viewing_dataframe
from utils.data_analysis import getJsonGraphData
from utils.recap_payload import HEAVY_RECAP_SECTIONS


logger = logging.getLogger(__name__)
QUEUE_NAME = "recaps"
RECAP_JOB_TIMEOUT_SECONDS = 60 * 30
INITIAL_RECAP_SECTIONS = [
    "total_title_watchtime",
    "total_type_watchtime",
    "monthly_watchtime",
    "ratings_watchtime",
    "core_stats",
    "title_level_insights",
    "wrapped_cards",
]


def recap_job_id(job_id):
    return f"recap-upload-{job_id}"


def enqueue_anonymous_recap(job_id, owner, profile_years):
    queue = django_rq.get_queue(QUEUE_NAME)
    return queue.enqueue(
        process_anonymous_upload,
        job_id,
        owner,
        profile_years,
        job_id=recap_job_id(job_id),
        job_timeout=RECAP_JOB_TIMEOUT_SECONDS,
        result_ttl=ANONYMOUS_CACHE_TTL_SECONDS,
        failure_ttl=ANONYMOUS_CACHE_TTL_SECONDS,
    )


def enqueue_authenticated_recap(job_id, owner, user_id, profile_years, source_filename):
    queue = django_rq.get_queue(QUEUE_NAME)
    return queue.enqueue(
        process_authenticated_upload,
        job_id,
        owner,
        user_id,
        profile_years,
        source_filename,
        job_id=recap_job_id(job_id),
        job_timeout=RECAP_JOB_TIMEOUT_SECONDS,
        result_ttl=ANONYMOUS_CACHE_TTL_SECONDS,
        failure_ttl=ANONYMOUS_CACHE_TTL_SECONDS,
    )


def process_authenticated_upload(job_id, owner, user_id, profile_years, source_filename):
    from django.contrib.auth import get_user_model

    _, dataframe = load_upload(owner, job_id)
    if dataframe is None:
        raise RuntimeError("Cached upload not found")

    user = get_user_model().objects.get(id=user_id)
    ingest_viewing_dataframe(user, dataframe, source_filename=source_filename)
    process_anonymous_upload(job_id, owner, profile_years)
    _warm_recommendations(user, profile_years)


def _warm_recommendations(user, profile_years):
    profiles = user.netflix_profiles.filter(name__in=profile_years.keys())
    for profile in profiles:
        try:
            generate_recommendations(profile)
        except RecommendationError:
            logger.info(
                "Recommendation warmup skipped for profile %s",
                profile.name,
                exc_info=True,
            )
        except Exception:
            logger.exception(
                "Recommendation warmup failed for profile %s",
                profile.name,
            )


def process_anonymous_upload(job_id, owner, profile_years):
    try:
        update_processing_state(
            job_id,
            worker_started_at=timezone.now().isoformat(),
        )
        logger.info("Starting queued recap processing for job %s", job_id)
        _, dataframe = load_upload(owner, job_id)
        if dataframe is None:
            raise RuntimeError("Cached upload not found")

        pending = {
            (profile_name, year)
            for profile_name, years in profile_years.items()
            for year in years
        }
        while pending:
            selected_profile = (
                get_processing_state(job_id) or {}
            ).get("selected_profile")
            profile_name, year = min(
                pending,
                key=lambda combination: (
                    0
                    if selected_profile
                    and combination[0] == selected_profile
                    else 1,
                    -int(combination[1]),
                    combination[0].lower(),
                ),
            )
            pending.remove((profile_name, year))
            process_profile_year(
                dataframe,
                owner,
                job_id,
                profile_name,
                year,
            )

        cache.set(
            job_status_key(job_id),
            "completed",
            timeout=ANONYMOUS_CACHE_TTL_SECONDS,
        )
        update_processing_state(
            job_id,
            job_status="completed",
            worker_finished_at=timezone.now().isoformat(),
        )
        logger.info("Queued recap processing completed for job %s", job_id)
    except Exception as exc:
        logger.exception("Queued recap processing failed for job %s", job_id)
        cache.set(
            job_status_key(job_id),
            f"error: {exc}",
            timeout=ANONYMOUS_CACHE_TTL_SECONDS,
        )
        update_processing_state(
            job_id,
            job_status="error",
            worker_finished_at=timezone.now().isoformat(),
        )
        raise


def process_profile_year(
    dataframe,
    owner,
    job_id,
    profile_name,
    year,
):
    cache_key = result_cache_key(owner, profile_name, year)
    cached_result = cache.get(cache_key)
    if cached_result and not cached_result.get("_partial"):
        update_processing_state(job_id, profile_name, year, "ready")
        return

    update_processing_state(job_id, profile_name, year, "processing")
    try:
        profile_year_df = filter_profile_year(
            dataframe,
            profile_name,
            year,
        )
        if profile_year_df.empty:
            raise ValueError("No data found for this profile and year")

        graph_data = getJsonGraphData(
            profile_year_df,
            profile_name,
            year,
        )
        graph_data["_partial"] = False
        graph_data["_full_ready_at"] = timezone.now().isoformat()
        graph_data["profile_comparisons"] = (
            profile_comparisons_from_dataframe(
                dataframe,
                profile_name,
                year,
            )
        )
        cache.set(
            cache_key,
            graph_data,
            timeout=ANONYMOUS_CACHE_TTL_SECONDS,
        )
        update_processing_state(job_id, profile_name, year, "ready")
    except Exception:
        logger.exception(
            "Failed processing %s - %s",
            profile_name,
            year,
        )
        update_processing_state(job_id, profile_name, year, "error")


def process_initial_profile_year(
    dataframe,
    owner,
    job_id,
    profile_name,
    year,
):
    cache_key = result_cache_key(owner, profile_name, year)
    cached_result = cache.get(cache_key)
    if cached_result:
        if cached_result.get("_partial"):
            update_processing_state(job_id, profile_name, year, "partial_ready")
        else:
            update_processing_state(job_id, profile_name, year, "ready")
        return

    update_processing_state(job_id, profile_name, year, "processing")
    try:
        profile_year_df = filter_profile_year(
            dataframe,
            profile_name,
            year,
        )
        if profile_year_df.empty:
            raise ValueError("No data found for this profile and year")

        graph_data = getJsonGraphData(
            profile_year_df,
            profile_name,
            year,
            sections=INITIAL_RECAP_SECTIONS,
        )
        graph_data["_partial"] = True
        graph_data["_sections_ready"] = INITIAL_RECAP_SECTIONS
        graph_data["_sections_pending"] = sorted(HEAVY_RECAP_SECTIONS)
        graph_data["_partial_ready_at"] = timezone.now().isoformat()
        cache.set(
            cache_key,
            graph_data,
            timeout=ANONYMOUS_CACHE_TTL_SECONDS,
        )
        update_processing_state(job_id, profile_name, year, "partial_ready")
    except Exception:
        logger.exception(
            "Failed initial processing %s - %s",
            profile_name,
            year,
        )
        update_processing_state(job_id, profile_name, year, "error")
