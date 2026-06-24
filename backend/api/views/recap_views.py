from collections import defaultdict
import logging
import uuid

import pandas as pd
from django.core.cache import cache
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from redis.exceptions import RedisError

from utils.data_analysis import getJsonGraphData

from ..authentication import JWTCookieAuthentication
from ..models import NetflixProfile, ViewingEvent
from ..services.recap_cache import (
    ANONYMOUS_CACHE_TTL_SECONDS,
    anonymous_expiry,
    create_processing_state,
    get_processing_state,
    job_status_key,
    load_upload,
    owner_key,
    processing_status_payload,
    ready_profile_years,
    result_cache_key,
    set_processing_state,
    store_upload,
    update_processing_state,
    upload_cache_key,
)
from ..services.recap_data import (
    filter_profile_year,
    is_all_years,
    profile_comparisons_from_dataframe,
    profile_events,
    repair_cached_graph_data,
    saved_or_generated_recap,
    year_comparison_payload,
)
from ..services.recap_jobs import (
    enqueue_authenticated_recap,
    enqueue_anonymous_recap,
    process_initial_profile_year,
)
from ..utils import validate_csv_columns


logger = logging.getLogger(__name__)

def get_authenticated_user(request):
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return user
    return None


def get_requested_recap(request, profile_field="profile_name"):
    return (
        str(request.data.get(profile_field) or "").strip(),
        request.data.get("year"),
        request.data.get("job_id"),
    )


def ready_response(graph_data):
    return Response({"status": "ready", "data": graph_data})


def not_found_response(message="Data not found"):
    return Response(
        {"status": "not_found", "message": message},
        status=status.HTTP_404_NOT_FOUND,
    )


def default_profile_year(profile_years_map):
    for profile_name in sorted(profile_years_map):
        years = sorted(profile_years_map[profile_name], reverse=True)
        if years:
            return profile_name, years[0]
    return None, None


class ViewingHistoryUploadView(APIView):
    """
    Quick extraction that immediately returns profile/year options
    and starts background processing
    """
    parser_classes = [MultiPartParser, FormParser]
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [AllowAny]

    @validate_csv_columns
    def post(self, request, format=None):
        logger.info("Received viewing history upload")

        uploaded_files = request.FILES.getlist("files") or request.FILES.getlist("file")
        if not uploaded_files:
            return Response({"error": "Missing file"}, status=status.HTTP_400_BAD_REQUEST)
        user_obj = get_authenticated_user(request)

        try:
            # Quick validation and profile/year extraction
            raw_row_count = sum(len(csv_df) for csv_df in getattr(request, "csv_dfs", []))
            df = request.csv_df.copy()
            before_dedup_count = len(df)
            df = df.drop_duplicates(
                subset=["Profile Name", "Start Time", "Duration", "Title"],
                keep="first",
            )
            duplicate_count = before_dedup_count - len(df)
            source_filename = ", ".join(getattr(file, "name", "upload.csv") for file in uploaded_files)
            logger.info("Validated viewing history with %s rows", len(df))
            # Quick extraction of profile/year combinations
            df['parsed_start_time'] = pd.to_datetime(df["Start Time"], errors="coerce")
            df = df.dropna(subset=['parsed_start_time', 'Profile Name'])
            df['year'] = df['parsed_start_time'].dt.year

            profile_year_df = df.groupby(['Profile Name', 'year']).size().reset_index(name='count')
            
            profile_years_map = defaultdict(set)
            for _, row in profile_year_df.iterrows():
                profile_years_map[row['Profile Name']].add(int(row['year']))
            
            profile_years_map = {
                profile: sorted(list(years)) 
                for profile, years in profile_years_map.items()
            }

            job_id = str(uuid.uuid4())
            recap_owner = owner_key(user_obj, job_id)
            expires_at = None if user_obj else anonymous_expiry()

            processing_state = create_processing_state(
                profile_years_map,
                status_value="queued",
                expires_at=expires_at,
            )

            upload_data = {
                "dataframe_json": df.to_json(orient="records"),
                "profile_years_map": profile_years_map,
                "owner_key": recap_owner,
                "job_id": job_id,
                "expires_at": expires_at.isoformat() if expires_at else None,
            }
            store_upload(recap_owner, job_id, upload_data)
            set_processing_state(job_id, processing_state)

            initial_profile, initial_year = default_profile_year(profile_years_map)
            if initial_profile and initial_year:
                process_initial_profile_year(
                    df,
                    recap_owner,
                    job_id,
                    initial_profile,
                    initial_year,
                )
                update_processing_state(
                    job_id,
                    selected_profile=initial_profile,
                )

            processing_state = get_processing_state(job_id) or processing_state
            if processing_state.get("processed", 0) + processing_state.get("failed", 0) >= processing_state.get("total", 0):
                update_processing_state(job_id, job_status="completed")
                processing_state = get_processing_state(job_id) or processing_state
                cache.set(
                    job_status_key(job_id),
                    "completed",
                    timeout=ANONYMOUS_CACHE_TTL_SECONDS,
                )
            else:
                if user_obj:
                    enqueue_authenticated_recap(
                        job_id,
                        recap_owner,
                        user_obj.id,
                        profile_years_map,
                        source_filename,
                    )
                else:
                    enqueue_anonymous_recap(job_id, recap_owner, profile_years_map)

            return Response({
                "message": "CSV uploaded successfully. Processing in background.",
                "profile_years": profile_years_map,
                "ready_profile_years": ready_profile_years(processing_state),
                "processing_state": processing_state,
                "job_id": job_id,
                "status": processing_state.get("status", "processing"),
                "is_persisted": bool(user_obj),
                "expires_at": expires_at.isoformat() if expires_at else None,
                "merge_stats": {
                    "files_uploaded": len(uploaded_files),
                    "rows_read": raw_row_count,
                    "duplicates_skipped": duplicate_count,
                    "rows_accepted": len(df),
                },
            })

        except RedisError:
            logger.exception("Redis is unavailable during viewing history upload")
            return Response(
                {
                    "error": (
                        "Background processing is temporarily unavailable. "
                        "Start Redis and the recap worker, then try again."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.exception("Viewing history upload failed")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RecapDataView(APIView):
    """
    Endpoint to get processed data - now with priority processing
    """
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        user_obj = get_authenticated_user(request)
        profile_name, year, job_id = get_requested_recap(
            request,
            profile_field="user",
        )
        recap_owner = owner_key(user_obj, job_id)

        if not profile_name or not year:
            return Response(
                {"error": "Profile name and year are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Check if data is already processed
            if user_obj:
                profile, events = profile_events(
                    user_obj,
                    profile_name,
                    year,
                )
                if profile and events.exists():
                    graph_data = saved_or_generated_recap(
                        user_obj,
                        profile,
                        events,
                        profile_name,
                        year,
                    )
                    return ready_response(graph_data)

            cached_result = cache.get(
                result_cache_key(recap_owner, profile_name, year)
            )
            if cached_result:
                cached_result = repair_cached_graph_data(
                    cached_result,
                    recap_owner,
                    job_id,
                    profile_name,
                    year,
                )
                return ready_response(cached_result)
            if job_id:
                if not cache.get(upload_cache_key(recap_owner, job_id)):
                    return Response(
                        {
                            "status": "expired",
                            "message": "Temporary upload expired. Upload the CSV again.",
                        },
                        status=status.HTTP_410_GONE,
                    )
                update_processing_state(
                    job_id,
                    selected_profile=profile_name,
                )
                return Response({
                    "status": "processing",
                    "message": f"Generating insights for {profile_name} - {year}...",
                })

            return Response({
                "status": "not_found",
                "message": "Data not available and no job ID provided",
            })

        except Exception as exc:
            logger.exception(
                "Failed loading recap data for %s - %s",
                profile_name,
                year,
            )
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class RecapProcessingStatusView(APIView):
    """
    Endpoint to check the status of background processing
    """
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, job_id, format=None):
        try:
            processing_state = get_processing_state(job_id)
            if processing_state:
                return Response(
                    processing_status_payload(
                        job_id,
                        processing_state,
                        message="Processing status loaded from Redis",
                    )
                )

            cached_status = cache.get(job_status_key(job_id))
            if cached_status == "completed":
                return Response(
                    processing_status_payload(
                        job_id,
                        {"percent": 100},
                        status_value="completed",
                        message="Processing completed",
                    )
                )
            if isinstance(cached_status, str) and cached_status.startswith("error:"):
                return Response(
                    processing_status_payload(
                        job_id,
                        status_value="error",
                        message="Processing failed",
                        error=cached_status[6:],
                    )
                )

            return Response(
                processing_status_payload(
                    job_id,
                    status_value="expired",
                    message="Temporary upload expired. Upload the CSV again.",
                )
            )

        except Exception as exc:
            logger.exception("Failed to load processing status for job %s", job_id)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class YearComparisonView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        user_obj = get_authenticated_user(request)
        profile_name = str(request.data.get("profile_name") or "").strip()
        year_a = request.data.get("year_a")
        year_b = request.data.get("year_b")
        job_id = request.data.get("job_id")

        if not profile_name or not year_a or not year_b:
            return Response(
                {"error": "profile_name, year_a, and year_b are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if int(year_a) == int(year_b):
            return Response(
                {"error": "Choose two different years to compare."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if user_obj:
                profile = NetflixProfile.objects.filter(
                    user=user_obj,
                    name=profile_name,
                ).first()
                if not profile:
                    return not_found_response("Profile not found")

                events_a = ViewingEvent.objects.filter(profile=profile, started_at__year=int(year_a))
                events_b = ViewingEvent.objects.filter(profile=profile, started_at__year=int(year_b))
                if not events_a.exists() or not events_b.exists():
                    return not_found_response("One or both years are missing")

                graph_a = saved_or_generated_recap(
                    user_obj,
                    profile,
                    events_a,
                    profile_name,
                    year_a,
                )
                graph_b = saved_or_generated_recap(
                    user_obj,
                    profile,
                    events_b,
                    profile_name,
                    year_b,
                )
                return Response({
                    "status": "ready",
                    "data": year_comparison_payload(
                        year_a,
                        graph_a,
                        year_b,
                        graph_b,
                    ),
                })

            if not job_id:
                return Response({"status": "not_found", "message": "Anonymous comparisons require a job_id"}, status=404)

            recap_owner = owner_key(None, job_id)
            csv_data, df = load_upload(recap_owner, job_id)
            if df is None:
                return Response({"status": "expired", "message": "Temporary upload expired"}, status=404)

            graphs = []
            for year in [year_a, year_b]:
                profile_year_df = filter_profile_year(df, profile_name, year)
                if len(profile_year_df) == 0:
                    return not_found_response(f"No data found for {year}")
                graph_data = getJsonGraphData(profile_year_df, profile_name, year)
                graph_data["profile_comparisons"] = profile_comparisons_from_dataframe(
                    df,
                    profile_name,
                    year,
                )
                graphs.append(graph_data)

            return Response({
                "status": "ready",
                "data": year_comparison_payload(
                    year_a,
                    graphs[0],
                    year_b,
                    graphs[1],
                ),
                "expires_at": csv_data.get("expires_at"),
            })
        except Exception as exc:
            logger.exception(
                "Failed comparing years %s and %s for %s",
                year_a,
                year_b,
                profile_name,
            )
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AvailableRecapsView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        events = (
            ViewingEvent.objects
            .filter(profile__user=user)
            .values("profile__name", "started_at__year")
            .distinct()
        )
        
        available_recaps = {}
        for event in events:
            profile_name = event["profile__name"]
            year = event["started_at__year"]
            available_recaps.setdefault(profile_name, []).append(year)

        for profile_name, years in available_recaps.items():
            available_recaps[profile_name] = sorted(set(years), reverse=True)
        
        return Response(available_recaps)

class SavedRecapView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        profile_name, year, _ = get_requested_recap(request)
        if not profile_name or not year:
            return Response(
                {"error": "profile_name and year are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile, events = profile_events(
            request.user,
            profile_name,
            year,
        )
        if not profile or not events.exists():
            return not_found_response()

        graph_data = saved_or_generated_recap(
            request.user,
            profile,
            events,
            profile_name,
            year,
        )
        return ready_response(graph_data)
