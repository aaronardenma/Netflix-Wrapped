from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
import pandas as pd
from django.utils import timezone
from django.db import transaction
from utils.csv_utils import validate_csv
from utils.data_analysis import getJsonGraphData
from api.serializers import UploadCSVSerializer
from ..utils import validate_csv_columns
from ..models import ViewingStat
from rest_framework.permissions import IsAuthenticated
from ..authentication import JWTCookieAuthentication
from collections import defaultdict
import threading
import uuid
from django.core.cache import cache
import json
import time


# Global dictionary to track background threads
background_threads = {}
priority_locks = {}  # To coordinate priority processing
priority_processing = {}  # Track active priority processing jobs: {(user_id, profile, year): job_id}


class QuickExtractCSVView(APIView):
    """
    Quick extraction that immediately returns profile/year options
    and starts background processing
    """
    parser_classes = [MultiPartParser, FormParser]
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    @validate_csv_columns
    def post(self, request, format=None):
        print("Received request to QuickExtractCSVView")

        serializer = UploadCSVSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = serializer.validated_data['file']
        user_obj = request.user

        try:
            # Quick validation and profile/year extraction
            df = validate_csv(file)
            print(f"CSV validated. Total rows: {len(df)}")

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
            cache_key = f"csv_data_{user_obj.id}_{job_id}"
            
            # Ensure all data is JSON serializable
            csv_data = {
                'dataframe_json': df.to_json(orient='records'),
                'profile_years_map': profile_years_map,
                'user_id': str(user_obj.id),  # Convert to string upfront
                'job_id': job_id  # Already a string
            }
            
            # Convert to JSON string manually to handle any remaining serialization issues
            try:
                json_data = json.dumps(csv_data)
                cache.set(cache_key, json_data, timeout=1800)  # 30 minutes
            except TypeError as e:
                print(f"JSON serialization error: {e}")
                print(f"CSV data keys: {csv_data.keys()}")
                print(f"User ID type: {type(user_obj.id)}")
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
            
            # Start background processing thread
            background_thread = threading.Thread(
                target=self.process_all_data_in_background,
                args=(cache_key, user_obj.id, job_id, profile_years_map),
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
                "job_id": job_id,
                "status": "processing"
            })

        except Exception as e:
            print(f"Exception in QuickExtractCSVView: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def process_all_data_in_background(self, cache_key, user_id, job_id, profile_years_map):
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
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user_obj = User.objects.get(id=user_id)

            # Get current date for year completion logic
            current_date = timezone.now()

            # Get all combinations to process
            all_combinations = []
            for profile_name, years in profile_years_map.items():
                for year in years:
                    all_combinations.append((profile_name, year))

            # Filter combinations based on year completion and upload date logic
            combinations_to_process = []
            for profile_name, year in all_combinations:
                should_process = self.should_process_combination(
                    user_obj, profile_name, year, current_date
                )
                if should_process:
                    combinations_to_process.append((profile_name, year))
                else:
                    print(f"Skipping {profile_name} - {year} (year completed and data already uploaded after year end)")

            total_combinations = len(combinations_to_process)
            processed = 0

            print(f"Processing {total_combinations} out of {len(all_combinations)} total combinations")

            for profile_name, year in combinations_to_process:
                # Check if we need to pause for priority processing
                priority_event = priority_locks.get(job_id)
                if priority_event:
                    priority_event.wait()  # Wait if priority processing is happening

                # Double-check if this combination was already processed by priority request
                # during our processing (race condition protection)
                existing = ViewingStat.objects.filter(
                    user=user_obj,
                    profile_name=profile_name,
                    year=year
                ).first()
                
                if existing:
                    # Check if this was processed after we started (by priority request)
                    if existing.uploaded_at > current_date:
                        processed += 1
                        print(f"Skipping {profile_name} - {year} (processed by priority request during background processing)")
                        continue
                    # If it exists from before, we still want to update it with new data
                    print(f"Updating existing data for {profile_name} - {year}")

                processed += 1
                print(f"Background processing {profile_name} - {year} ({processed}/{total_combinations})")
                
                try:
                    # Process this combination
                    profile_year_mask = (df['Profile Name'] == profile_name) & (df['year'] == year)
                    profile_year_df = df[profile_year_mask].copy()
                    
                    if len(profile_year_df) > 0:
                        graph_data = getJsonGraphData(profile_year_df, profile_name, year)
                        
                        # Update existing or create new
                        viewing_stat, created = ViewingStat.objects.update_or_create(
                            user=user_obj,
                            profile_name=profile_name,
                            year=int(year),
                            defaults={
                                'data': graph_data,
                                'uploaded_at': timezone.now()
                            }
                        )
                        
                        action = "Created" if created else "Updated"
                        print(f"{action} ViewingStat for {profile_name} - {year}")
                            
                except Exception as e:
                    print(f"Error processing {profile_name} - {year}: {str(e)}")
                    continue

            # Mark as completed
            if job_id in background_threads:
                background_threads[job_id]['status'] = 'completed'
            cache.set(f"job_status_{job_id}", "completed", timeout=3600)
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

    def should_process_combination(self, user_obj, profile_name, year, current_date):
        """
        Determine if a profile/year combination should be processed based on:
        1. If the viewing year is not yet completed (current year or future), always process
        2. If the viewing year is completed, only process if:
        - No existing data exists, OR
        - Existing data was uploaded before the viewing year ended
        """
        viewing_year = int(year)
        current_year = current_date.year
        
        # If the viewing year is not yet completed (current year or future), always process
        if viewing_year >= current_year:
            return True
        
        # Viewing year is completed (past year)
        # Check if we have existing data for this combination
        existing = ViewingStat.objects.filter(
            user=user_obj,
            profile_name=profile_name,
            year=viewing_year
        ).first()
        
        if not existing:
            # No existing data, so process it
            return True
        
        # We have existing data, check when it was uploaded
        viewing_year_end_date = timezone.datetime(
            viewing_year + 1, 1, 1, tzinfo=timezone.get_current_timezone()
        )
        
        # If the existing data was uploaded after the viewing year ended, don't reprocess
        if existing.uploaded_at >= viewing_year_end_date:
            return False
        
        # If the existing data was uploaded before/during the viewing year, reprocess with new data
        return True


class PriorityProcessView(APIView):
    """
    Process a specific user/year combination with priority
    """
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        user_obj = request.user
        profile_name = request.data.get('user')
        year = request.data.get('year')
        job_id = request.data.get('job_id')

        if not profile_name or not year:
            return Response(
                {"error": "Profile name and year are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # First check if data already exists
            existing_stat = ViewingStat.objects.filter(
                user=user_obj,
                profile_name=profile_name,
                year=year
            ).first()

            if existing_stat:
                return Response({
                    "status": "ready",
                    "data": existing_stat.data
                })

            # If not ready, process with priority
            if job_id and job_id in priority_locks:
                # Pause background processing temporarily
                priority_event = priority_locks[job_id]
                priority_event.clear()  # Pause background thread
                
                try:
                    # Process this specific combination immediately
                    result = self.process_priority_combination(
                        user_obj, profile_name, year, job_id
                    )
                    
                    if result['status'] == 'success':
                        return Response({
                            "status": "ready",
                            "data": result['data']
                        })
                    else:
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

    def process_priority_combination(self, user_obj, profile_name, year, job_id):
        """
        Process a specific profile/year combination immediately
        """
        try:
            # Get cached data
            cache_key = f"csv_data_{user_obj.id}_{job_id}"
            cached_data = cache.get(cache_key)
            
            if not cached_data:
                return {'status': 'error', 'error': 'Cached data not found'}
            
            csv_data = json.loads(cached_data)
            
            # Fix pandas FutureWarning by using StringIO
            import io
            df_json_str = csv_data['dataframe_json']
            df = pd.read_json(io.StringIO(df_json_str), orient='records')
            
            # Filter for specific combination
            profile_year_mask = (df['Profile Name'] == profile_name) & (df['year'] == int(year))
            profile_year_df = df[profile_year_mask].copy()
            
            if len(profile_year_df) == 0:
                return {'status': 'error', 'error': 'No data found for this combination'}
            
            print(f"Priority processing {profile_name} - {year}")
            
            # Generate graph data
            graph_data = getJsonGraphData(profile_year_df, profile_name, year)
            
            # Save to database
            viewing_stat = ViewingStat.objects.create(
                user=user_obj,
                profile_name=profile_name,
                year=int(year),
                data=graph_data,
                uploaded_at=timezone.now()
            )
            
            return {'status': 'success', 'data': graph_data}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


class GetDataView(APIView):
    """
    Endpoint to get processed data - now with priority processing
    """
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        user_obj = request.user
        profile_name = request.data.get('user')
        year = request.data.get('year')
        job_id = request.data.get('job_id')

        if not profile_name or not year:
            return Response(
                {"error": "Profile name and year are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Check if data is already processed
            viewing_stat = ViewingStat.objects.filter(
                user=user_obj,
                profile_name=profile_name,
                year=year
            ).first()

            if viewing_stat:
                return Response({
                    "status": "ready",
                    "data": viewing_stat.data
                })
            else:
                # Check if priority processing is already running for this combination
                priority_key = (user_obj.id, profile_name, year)
                if priority_key in priority_processing:
                    return Response({
                        "status": "priority_processing", 
                        "message": f"Already processing {profile_name} - {year} with priority..."
                    })
                
                # If not ready, trigger priority processing
                if job_id:
                    # Mark this combination as being processed
                    priority_processing[priority_key] = job_id
                    
                    # Call priority processing in a separate thread for immediate response
                    priority_thread = threading.Thread(
                        target=self.trigger_priority_processing,
                        args=(user_obj, profile_name, year, job_id, priority_key),
                        daemon=True
                    )
                    priority_thread.start()
                    
                    return Response({
                        "status": "priority_processing",
                        "message": f"Processing {profile_name} - {year} with priority..."
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

    def trigger_priority_processing(self, user_obj, profile_name, year, job_id, priority_key):
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
                'job_id': job_id
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
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id, format=None):
        """
        Get the current status of a processing job
        """
        try:
            # Check if job exists in background threads
            if job_id in background_threads:
                thread_info = background_threads[job_id]
                status_info = {
                    'status': thread_info['status'],
                    'job_id': job_id
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
                if cached_status:
                    if cached_status == 'completed':
                        return Response({
                            'status': 'completed',
                            'job_id': job_id,
                            'message': 'Processing completed'
                        })
                    elif cached_status.startswith('error:'):
                        return Response({
                            'status': 'error',
                            'job_id': job_id,
                            'message': 'Processing failed',
                            'error': cached_status[6:]  # Remove 'error:' prefix
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
        # Get all ViewingStat records for this user
        stats = ViewingStat.objects.filter(user=user).values('profile_name', 'year').distinct()
        
        # Group by profile_name
        data = {}
        for stat in stats:
            profile = stat['profile_name']
            year = stat['year']
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
            viewing_stat = ViewingStat.objects.get(
                user=user,
                profile_name=profile_name,
                year=year
            )
            return Response({
                'status': 'ready',
                'data': viewing_stat.data
            })
        except ViewingStat.DoesNotExist:
            return Response({
                'status': 'not_found',
                'message': 'Data not found'
            }, status=404)
