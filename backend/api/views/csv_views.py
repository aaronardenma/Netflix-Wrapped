from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
import pandas as pd
from utils.csv_utils import validate_csv
from utils.data_analysis import getJsonGraphData, getProfileComparisonData
from api.serializers import UploadCSVSerializer
from ..utils import validate_csv_columns
from ..models import NetflixProfile, ViewingEvent
from ..services.viewing_ingestion import ingest_viewing_dataframe
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from ..authentication import JWTCookieAuthentication
from collections import defaultdict
import threading
import uuid
from django.core.cache import cache
import json
import hashlib


# Global dictionary to track background threads
background_threads = {}
priority_locks = {}  # To coordinate priority processing
priority_processing = {}  # Track active priority processing jobs: {(owner_key, profile, year): job_id}


def get_authenticated_user(request):
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return user
    return None


def get_owner_key(user_obj, job_id):
    if user_obj:
        return f"user:{user_obj.id}"
    return f"anonymous:{job_id}"


def get_csv_cache_key(owner_key, job_id):
    return f"csv_data_{owner_key}_{job_id}"


def get_result_cache_key(owner_key, profile_name, year):
    profile_hash = hashlib.sha256(str(profile_name).encode("utf-8")).hexdigest()[:16]
    year_key = "all" if is_all_years(year) else str(int(year))
    return f"processed_data_{owner_key}_{profile_hash}_{year_key}"


def is_all_years(year):
    return str(year).lower() == "all"


def get_display_year(year):
    return "all" if is_all_years(year) else int(year)


def get_processing_state_key(job_id):
    return f"processing_state_{job_id}"


def create_processing_state(profile_years_map, status_value="queued"):
    profiles = {}
    for profile_name, years in profile_years_map.items():
        profiles[profile_name] = {
            str(year): status_value for year in sorted(years, reverse=True)
        }
    return {
        "status": "running",
        "profile_years": {
            profile_name: sorted(years, reverse=True)
            for profile_name, years in profile_years_map.items()
        },
        "profiles": profiles,
        "selected_profile": None,
    }


def get_processing_state(job_id):
    return cache.get(get_processing_state_key(job_id))


def set_processing_state(job_id, state, timeout=3600):
    cache.set(get_processing_state_key(job_id), state, timeout=timeout)


def update_processing_state(job_id, profile_name=None, year=None, year_status=None, job_status=None, selected_profile=None):
    state = get_processing_state(job_id) or {}
    if job_status:
        state["status"] = job_status
    if selected_profile is not None:
        state["selected_profile"] = selected_profile
    if profile_name is not None and year is not None and year_status:
        profiles = state.setdefault("profiles", {})
        profile_state = profiles.setdefault(profile_name, {})
        profile_state[str(year)] = year_status
    set_processing_state(job_id, state)
    return state


def get_ready_profile_years(state):
    ready = {}
    for profile_name, years in (state or {}).get("profiles", {}).items():
        ready_years = [
            int(year)
            for year, year_status in years.items()
            if year_status == "ready"
        ]
        if ready_years:
            ready[profile_name] = sorted(ready_years, reverse=True)
    return ready


def seconds_to_duration_string(seconds):
    seconds = int(seconds or 0)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"


def get_event_rows_from_events(events):
    event_rows = []
    for event in events.select_related("profile").order_by("started_at"):
        event_rows.append({
            "Profile Name": event.profile.name,
            "Start Time": event.started_at,
            "Duration": seconds_to_duration_string(event.duration_seconds),
            "Attributes": "",
            "Title": event.title_raw,
            "Supplemental Video Type": event.supplemental_video_type or None,
            "Device Type": event.device_type,
            "Bookmark": "",
            "Latest Bookmark": "",
            "Country": event.country,
        })
    return event_rows


def get_graph_data_from_events(events, profile_name, year):
    return getJsonGraphData(pd.DataFrame(get_event_rows_from_events(events)), profile_name, get_display_year(year))


def get_profile_comparisons(user, profile_name, year):
    year_events = ViewingEvent.objects.filter(profile__user=user)
    if not is_all_years(year):
        year_events = year_events.filter(started_at__year=int(year))
    if not year_events.exists():
        return {}
    return getProfileComparisonData(
        pd.DataFrame(get_event_rows_from_events(year_events)),
        profile_name,
        get_display_year(year),
    )


class QuickExtractCSVView(APIView):
    """
    Quick extraction that immediately returns profile/year options
    and starts background processing
    """
    parser_classes = [MultiPartParser, FormParser]
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [AllowAny]

    @validate_csv_columns
    def post(self, request, format=None):
        print("Received request to QuickExtractCSVView")

        serializer = UploadCSVSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = serializer.validated_data['file']
        user_obj = get_authenticated_user(request)

        try:
            # Quick validation and profile/year extraction
            df = validate_csv(file)
            print(f"CSV validated. Total rows: {len(df)}")
            if user_obj:
                ingest_viewing_dataframe(
                    user_obj,
                    df,
                    source_filename=getattr(file, "name", ""),
                )

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

            # Store CSV data for both background and priority processing
            job_id = str(uuid.uuid4())
            owner_key = get_owner_key(user_obj, job_id)
            cache_key = get_csv_cache_key(owner_key, job_id)
            
            # Ensure all data is JSON serializable
            csv_data = {
                'dataframe_json': df.to_json(orient='records'),
                'profile_years_map': profile_years_map,
                'user_id': str(user_obj.id) if user_obj else None,
                'owner_key': owner_key,
                'job_id': job_id  # Already a string
            }
            
            # Convert to JSON string manually to handle any remaining serialization issues
            try:
                json_data = json.dumps(csv_data)
                cache.set(cache_key, json_data, timeout=1800)  # 30 minutes
            except TypeError as e:
                print(f"JSON serialization error: {e}")
                print(f"CSV data keys: {csv_data.keys()}")
                print(f"User ID type: {type(user_obj.id) if user_obj else None}")
                print(f"Job ID type: {type(job_id)}")
                # Debug: try to identify what's not serializable
                for key, value in csv_data.items():
                    try:
                        json.dumps(value)
                        print(f"✓ {key} is serializable")
                    except TypeError as debug_e:
                        print(f"✗ {key} is not serializable: {debug_e}")
                raise e

            # Initialize coordination objects
            priority_locks[job_id] = threading.Event()
            priority_locks[job_id].set()
            processing_state = create_processing_state(
                profile_years_map,
                status_value="ready" if user_obj else "queued",
            )

            if user_obj:
                processing_state["status"] = "completed"
                set_processing_state(job_id, processing_state)
                background_threads[job_id] = {
                    'thread': None,
                    'status': 'completed',
                    'paused': False
                }
                cache.set(f"job_status_{job_id}", "completed", timeout=3600)
                return Response({
                    "message": "CSV uploaded successfully.",
                    "profile_years": profile_years_map,
                    "ready_profile_years": get_ready_profile_years(processing_state),
                    "processing_state": processing_state,
                    "job_id": job_id,
                    "status": "completed",
                    "is_persisted": True,
                })

            set_processing_state(job_id, processing_state)
            
            # Start background processing thread
            background_thread = threading.Thread(
                target=self.process_all_data_in_background,
                args=(
                    cache_key,
                    user_obj.id if user_obj else None,
                    job_id,
                    profile_years_map,
                    owner_key,
                ),
                daemon=True
            )
            background_threads[job_id] = {
                'thread': background_thread,
                'status': 'running',
                'paused': False
            }
            background_thread.start()

            return Response({
                "message": "CSV uploaded successfully. Processing in background.",
                "profile_years": profile_years_map,
                "ready_profile_years": {},
                "processing_state": processing_state,
                "job_id": job_id,
                "status": "processing",
                "is_persisted": bool(user_obj),
            })

        except Exception as e:
            print(f"Exception in QuickExtractCSVView: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def process_all_data_in_background(self, cache_key, user_id, job_id, profile_years_map, owner_key):
        """
        Background processing that can be paused for priority requests
        Only processes combinations that haven't been uploaded after the year completion
        """
        try:
            print(f"Starting background processing for job {job_id}")
            
            cached_data = cache.get(cache_key)
            if not cached_data:
                print(f"Cache data not found for job {job_id}")
                return
            
            csv_data = json.loads(cached_data)
            
            # Fix pandas FutureWarning by using StringIO
            import io
            df_json_str = csv_data['dataframe_json']
            df = pd.read_json(io.StringIO(df_json_str), orient='records')
            
            user_obj = None
            if user_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user_obj = User.objects.get(id=user_id)

            # Get all combinations to process
            all_combinations = []
            for profile_name, years in profile_years_map.items():
                for year in years:
                    all_combinations.append((profile_name, year))

            # Filter combinations based on year completion and upload date logic
            combinations_to_process = []
            for profile_name, year in all_combinations:
                should_process = self.should_process_combination(
                    user_obj, profile_name, year
                )
                if should_process:
                    combinations_to_process.append((profile_name, year))
                else:
                    print(f"Skipping {profile_name} - {year} (year completed and data already uploaded after year end)")

            pending_combinations = set(combinations_to_process)
            processed = 0

            print(f"Processing {len(pending_combinations)} out of {len(all_combinations)} total combinations")

            while pending_combinations:
                # Check if we need to pause for priority processing
                priority_event = priority_locks.get(job_id)
                if priority_event:
                    priority_event.wait()  # Wait if priority processing is happening

                state = get_processing_state(job_id) or {}
                selected_profile = state.get("selected_profile")
                ordered_combinations = sorted(
                    pending_combinations,
                    key=lambda combo: (
                        0 if selected_profile and combo[0] == selected_profile else 1,
                        -int(combo[1]),
                        combo[0].lower(),
                    ),
                )
                profile_name, year = ordered_combinations[0]
                pending_combinations.remove((profile_name, year))

                if cache.get(get_result_cache_key(owner_key, profile_name, year)):
                    update_processing_state(job_id, profile_name, year, "ready")
                    continue

                processed += 1
                update_processing_state(job_id, profile_name, year, "processing")
                print(f"Background processing {profile_name} - {year} ({processed}/{len(combinations_to_process)})")
                
                try:
                    # Process this combination
                    profile_year_mask = (df['Profile Name'] == profile_name) & (df['year'] == year)
                    profile_year_df = df[profile_year_mask].copy()
                    
                    if len(profile_year_df) > 0:
                        graph_data = getJsonGraphData(profile_year_df, profile_name, year)
                        
                        cache.set(
                            get_result_cache_key(owner_key, profile_name, year),
                            graph_data,
                            timeout=3600,
                        )
                        print(f"Cached anonymous result for {profile_name} - {year}")
                        update_processing_state(job_id, profile_name, year, "ready")
                            
                except Exception as e:
                    print(f"Error processing {profile_name} - {year}: {str(e)}")
                    update_processing_state(job_id, profile_name, year, "error")
                    continue

            # Mark as completed
            if job_id in background_threads:
                background_threads[job_id]['status'] = 'completed'
            cache.set(f"job_status_{job_id}", "completed", timeout=3600)
            update_processing_state(job_id, job_status="completed")
            print(f"Background processing completed for job {job_id}")
            
            # Cleanup
            cache.delete(cache_key)
            if job_id in priority_locks:
                del priority_locks[job_id]
            
        except Exception as e:
            print(f"Background processing error for job {job_id}: {str(e)}")
            if job_id in background_threads:
                background_threads[job_id]['status'] = 'error'
            cache.set(f"job_status_{job_id}", f"error: {str(e)}", timeout=3600)
            update_processing_state(job_id, job_status="error")

    def should_process_combination(self, user_obj, profile_name, year):
        """
        Anonymous jobs need cached graph data. Authenticated uploads are served
        from normalized ViewingEvent rows and only need processing if no events exist.
        """
        viewing_year = int(year)

        if not user_obj:
            return True

        profile = NetflixProfile.objects.filter(user=user_obj, name=profile_name).first()
        if not profile:
            return True

        return not ViewingEvent.objects.filter(
            profile=profile,
            started_at__year=viewing_year
        ).exists()


class PriorityProcessView(APIView):
    """
    Process a specific user/year combination with priority
    """
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        user_obj = get_authenticated_user(request)
        profile_name = request.data.get('user')
        year = request.data.get('year')
        job_id = request.data.get('job_id')
        owner_key = get_owner_key(user_obj, job_id)
        if job_id and profile_name:
            update_processing_state(job_id, selected_profile=profile_name)
        if job_id and profile_name:
            update_processing_state(job_id, selected_profile=profile_name)

        if not profile_name or not year:
            return Response(
                {"error": "Profile name and year are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # First check if data already exists
            if user_obj:
                profile = NetflixProfile.objects.filter(user=user_obj, name=profile_name).first()
                if profile:
                    events = ViewingEvent.objects.filter(profile=profile)
                    if not is_all_years(year):
                        events = events.filter(started_at__year=int(year))
                    if events.exists():
                        graph_data = get_graph_data_from_events(events, profile_name, year)
                        graph_data["profile_comparisons"] = get_profile_comparisons(
                            user_obj,
                            profile_name,
                            year,
                        )
                        return Response({
                            "status": "ready",
                            "data": graph_data
                        })

            cached_result = cache.get(get_result_cache_key(owner_key, profile_name, year))
            if cached_result:
                return Response({
                    "status": "ready",
                    "data": cached_result
                })

            # If not ready, process with priority
            if job_id and job_id in priority_locks:
                # Pause background processing temporarily
                priority_event = priority_locks[job_id]
                priority_event.clear()  # Pause background thread
                
                try:
                    # Process this specific combination immediately
                    update_processing_state(job_id, profile_name, year, "processing")
                    result = self.process_priority_combination(
                        user_obj, profile_name, year, job_id, owner_key
                    )
                    
                    if result['status'] == 'success':
                        update_processing_state(job_id, profile_name, year, "ready")
                        return Response({
                            "status": "ready",
                            "data": result['data']
                        })
                    else:
                        update_processing_state(job_id, profile_name, year, "error")
                        return Response({
                            "status": "error",
                            "message": result['error']
                        })
                        
                finally:
                    # Resume background processing
                    priority_event.set()
            else:
                return Response({
                    "status": "error",
                    "message": "Job ID not found or invalid"
                })

        except Exception as e:
            print(f"Priority processing error: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def process_priority_combination(self, user_obj, profile_name, year, job_id, owner_key):
        """
        Process a specific profile/year combination immediately
        """
        try:
            # Get cached data
            cache_key = get_csv_cache_key(owner_key, job_id)
            cached_data = cache.get(cache_key)
            
            if not cached_data:
                return {'status': 'error', 'error': 'Cached data not found'}
            
            csv_data = json.loads(cached_data)
            
            # Fix pandas FutureWarning by using StringIO
            import io
            df_json_str = csv_data['dataframe_json']
            df = pd.read_json(io.StringIO(df_json_str), orient='records')
            
            # Filter for specific combination
            profile_year_mask = df['Profile Name'] == profile_name
            if not is_all_years(year):
                profile_year_mask = profile_year_mask & (df['year'] == int(year))
            profile_year_df = df[profile_year_mask].copy()
            
            if len(profile_year_df) == 0:
                return {'status': 'error', 'error': 'No data found for this combination'}
            
            print(f"Priority processing {profile_name} - {year}")
            
            # Generate graph data
            graph_data = getJsonGraphData(profile_year_df, profile_name, year)
            
            cache.set(
                get_result_cache_key(owner_key, profile_name, year),
                graph_data,
                timeout=3600,
            )
            update_processing_state(job_id, profile_name, year, "ready")
            
            return {'status': 'success', 'data': graph_data}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


class GetDataView(APIView):
    """
    Endpoint to get processed data - now with priority processing
    """
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        user_obj = get_authenticated_user(request)
        profile_name = request.data.get('user')
        year = request.data.get('year')
        job_id = request.data.get('job_id')
        owner_key = get_owner_key(user_obj, job_id)

        if not profile_name or not year:
            return Response(
                {"error": "Profile name and year are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Check if data is already processed
            if user_obj:
                profile = NetflixProfile.objects.filter(user=user_obj, name=profile_name).first()
                if profile:
                    events = ViewingEvent.objects.filter(profile=profile)
                    if not is_all_years(year):
                        events = events.filter(started_at__year=int(year))
                    if events.exists():
                        graph_data = get_graph_data_from_events(events, profile_name, year)
                        graph_data["profile_comparisons"] = get_profile_comparisons(
                            user_obj,
                            profile_name,
                            year,
                        )
                        return Response({
                            "status": "ready",
                            "data": graph_data,
                        })

            cached_result = cache.get(get_result_cache_key(owner_key, profile_name, year))
            if cached_result:
                return Response({
                    "status": "ready",
                    "data": cached_result
                })
            else:
                # Check if priority processing is already running for this combination
                priority_key = (owner_key, profile_name, year)
                if priority_key in priority_processing:
                    return Response({
                        "status": "processing", 
                        "message": f"Generating insights for {profile_name} - {year}..."
                    })
                
                # If not ready, trigger priority processing
                if job_id:
                    # Mark this combination as being processed
                    priority_processing[priority_key] = job_id
                    
                    # Call priority processing in a separate thread for immediate response
                    priority_thread = threading.Thread(
                        target=self.trigger_priority_processing,
                        args=(user_obj, profile_name, year, job_id, priority_key, owner_key),
                        daemon=True
                    )
                    priority_thread.start()
                    
                    return Response({
                        "status": "processing",
                        "message": f"Generating insights for {profile_name} - {year}..."
                    })
                else:
                    return Response({
                        "status": "not_found",
                        "message": "Data not available and no job ID provided"
                    })

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def trigger_priority_processing(self, user_obj, profile_name, year, job_id, priority_key, owner_key):
        """
        Trigger priority processing in background
        """
        try:
            priority_view = PriorityProcessView()
            # Simulate request object for the priority processing
            class MockRequest:
                def __init__(self, user, data):
                    self.user = user
                    self.data = data
            
            mock_request = MockRequest(user_obj, {
                'user': profile_name,
                'year': year,
                'job_id': job_id,
                'owner_key': owner_key,
            })
            
            priority_view.post(mock_request)
        finally:
            # Always remove from priority processing tracker when done
            if priority_key in priority_processing:
                del priority_processing[priority_key]


class ProcessingStatusView(APIView):
    """
    Endpoint to check the status of background processing
    """
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, job_id, format=None):
        """
        Get the current status of a processing job
        """
        try:
            # Check if job exists in background threads
            if job_id in background_threads:
                thread_info = background_threads[job_id]
                processing_state = get_processing_state(job_id)
                status_info = {
                    'status': thread_info['status'],
                    'job_id': job_id,
                    'profile_years': (processing_state or {}).get('profile_years', {}),
                    'profiles': (processing_state or {}).get('profiles', {}),
                    'ready_profile_years': get_ready_profile_years(processing_state),
                    'selected_profile': (processing_state or {}).get('selected_profile'),
                }
                
                # Add more details based on status
                if thread_info['status'] == 'running':
                    status_info['message'] = 'Processing in background...'
                elif thread_info['status'] == 'completed':
                    status_info['message'] = 'Processing completed'
                elif thread_info['status'] == 'error':
                    # Try to get error details from cache
                    cached_status = cache.get(f"job_status_{job_id}")
                    if cached_status and cached_status.startswith('error:'):
                        status_info['error'] = cached_status[6:]  # Remove 'error:' prefix
                    status_info['message'] = 'Processing failed'
                
                return Response(status_info)
            else:
                # Check cache for status
                cached_status = cache.get(f"job_status_{job_id}")
                processing_state = get_processing_state(job_id)
                if cached_status:
                    if cached_status == 'completed':
                        return Response({
                            'status': 'completed',
                            'job_id': job_id,
                            'message': 'Processing completed',
                            'profile_years': (processing_state or {}).get('profile_years', {}),
                            'profiles': (processing_state or {}).get('profiles', {}),
                            'ready_profile_years': get_ready_profile_years(processing_state),
                            'selected_profile': (processing_state or {}).get('selected_profile'),
                        })
                    elif cached_status.startswith('error:'):
                        return Response({
                            'status': 'error',
                            'job_id': job_id,
                            'message': 'Processing failed',
                            'error': cached_status[6:],  # Remove 'error:' prefix
                            'profile_years': (processing_state or {}).get('profile_years', {}),
                            'profiles': (processing_state or {}).get('profiles', {}),
                            'ready_profile_years': get_ready_profile_years(processing_state),
                            'selected_profile': (processing_state or {}).get('selected_profile'),
                        })
                
                # Job not found
                return Response({
                    'status': 'not_found',
                    'job_id': job_id,
                    'message': 'Job not found or expired'
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class StoredDataView(APIView):
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
        
        data = {}
        for event in events:
            profile = event["profile__name"]
            year = event["started_at__year"]
            if profile not in data:
                data[profile] = []
            data[profile].append(year)

        for profile in data:
            data[profile] = sorted(set(data[profile]), reverse=True)
        
        return Response(data)

class GetStoredDataView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        profile_name = request.data.get('profile_name')
        year = request.data.get('year')
        
        try:
            profile = NetflixProfile.objects.get(user=user, name=profile_name)
            events = ViewingEvent.objects.filter(profile=profile)
            if not is_all_years(year):
                events = events.filter(started_at__year=int(year))
            if events.exists():
                graph_data = get_graph_data_from_events(events, profile_name, year)
                graph_data["profile_comparisons"] = get_profile_comparisons(
                    user,
                    profile_name,
                    year,
                )
                return Response({
                    'status': 'ready',
                    'data': graph_data
                })
        except NetflixProfile.DoesNotExist:
            return Response({
                'status': 'not_found',
                'message': 'Data not found'
            }, status=404)

        return Response({
            'status': 'not_found',
            'message': 'Data not found'
        }, status=404)
