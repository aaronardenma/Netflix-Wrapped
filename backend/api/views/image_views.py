# views.py
import requests
import os
from rest_framework.response import Response

import json
import re
from rest_framework.views import APIView
from django.http import JsonResponse
from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from ..authentication import JWTCookieAuthentication
from django.views.decorators.csrf import csrf_exempt

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
OMDB_API_KEY = os.getenv("OMDB_API_KEY")  # optional
CACHE_TIMEOUT = 60 * 60 * 24 * 7  # 1 week

class FetchPosterView(APIView):
    """
    Fetches poster URL for a given title/year/type.
    Returns a placeholder if confidence is low.
    """
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            raw_title = request.data.get("title")
            year = request.data.get("year")
            content_type = request.data.get("type", "movie")

            print(f"[DEBUG] Incoming request: title={raw_title}, year={year}, type={content_type}")

            if not raw_title:
                print("[DEBUG] No title provided")
                return Response({
                    "poster_url": None,
                    "use_placeholder": True,
                    "cached": False,
                    "error": "Title is required"
                }, status=400)

            cache_key = f"poster:{raw_title}:{year}:{content_type}"
            cached_data = cache.get(cache_key)
            if cached_data:
                print(f"[DEBUG] Cache hit for key: {cache_key}")
                return Response(cached_data)

            normalized_title = self.normalize_title(raw_title)
            print(f"[DEBUG] Normalized title: {normalized_title}")

            poster_url, confidence = self.query_tmdb(normalized_title, year, content_type)
            print(f"[DEBUG] TMDb result: poster_url={poster_url}, confidence={confidence}")

            if not poster_url and OMDB_API_KEY:
                poster_url, confidence = self.query_omdb(normalized_title, year, content_type)
                print(f"[DEBUG] OMDb result: poster_url={poster_url}, confidence={confidence}")

            response_data = {}
            if confidence >= 2 and poster_url:
                response_data["poster_url"] = poster_url
                response_data["use_placeholder"] = False
            else:
                response_data["poster_url"] = None
                response_data["use_placeholder"] = True
                print("[DEBUG] Using placeholder due to low confidence")

            response_data["cached"] = False
            cache.set(cache_key, response_data, CACHE_TIMEOUT)
            print(f"[DEBUG] Response data cached under key {cache_key}")

            return Response(response_data)

        except Exception as e:
            print(f"[ERROR] Exception in FetchPosterView: {e}")
            return Response({"error": str(e)}, status=500)
    @staticmethod
    def normalize_title(title: str) -> str:
        import re
        clean = re.sub(r"\(.*?\)", "", title)
        return clean.strip()

    @staticmethod
    def query_tmdb(title: str, year=None, content_type="movie"):
        url = f"https://api.themoviedb.org/3/search/{content_type}"
        params = {"api_key": TMDB_API_KEY, "query": title}
        if year:
            if content_type == "movie":
                params["year"] = year
            else:
                params["first_air_date_year"] = year

        res = requests.get(url, params=params)
        if res.status_code != 200:
            print(f"[DEBUG] TMDb request failed with status {res.status_code}")
            return None, 0

        results = res.json().get("results", [])

        best_result = None
        highest_score = -1

        for r in results:
            score = 0

            # Exact title match gives higher score
            tmdb_title = r.get("title") if content_type == "movie" else r.get("name")
            if tmdb_title and tmdb_title.lower() == title.lower():
                score += 3  # exact match = high confidence

            # Year match gives moderate score
            release_date = r.get("release_date") or r.get("first_air_date")
            if year and release_date and release_date.startswith(str(year)):
                score += 1

            # Poster exists → add small bonus
            if r.get("poster_path"):
                score += 1

            if score > highest_score:
                highest_score = score
                best_result = r

        if best_result and best_result.get("poster_path"):
            poster_url = f"https://image.tmdb.org/t/p/w500{best_result['poster_path']}"
            print(f"[DEBUG] TMDb best match: title={best_result.get('title') or best_result.get('name')}, score={highest_score}, poster={poster_url}")
            return poster_url, highest_score

        return None, highest_score


    @staticmethod
    def query_omdb(title: str, year=None, content_type="movie"):
        import requests, os
        OMDB_API_KEY = os.getenv("OMDB_API_KEY")
        url = "http://www.omdbapi.com/"
        params = {"apikey": OMDB_API_KEY, "t": title, "type": content_type}
        if year:
            params["y"] = year

        res = requests.get(url, params=params)
        if res.status_code != 200:
            return None, 0
        data = res.json()
        poster = data.get("Poster")
        confidence = 0
        if poster and poster != "N/A":
            confidence = 2
            return poster, confidence
        return None, confidence