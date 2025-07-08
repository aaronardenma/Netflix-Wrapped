from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
import pandas as pd
from utils.data_analysis import getJsonGraphData

EXPECTED_COLUMNS = [
    "Profile Name",
    "Start Time",
    "Duration",
    "Attributes",
    "Title",
    "Supplemental Video Type",
    "Device Type",
    "Bookmark",
    "Latest Bookmark",
    "Country"
]

class UploadCSVView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        file_obj = request.FILES.get('file')
        user = request.data.get('user')
        year = request.data.get('year')

        if not file_obj or not user or not year:
            return Response({"error": "Missing file, user, or year"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_csv(file_obj)

            if list(df.columns) != EXPECTED_COLUMNS:
                return Response({
                    "error": "CSV headers do not match expected Netflix viewing data columns.",
                    "expected_columns": EXPECTED_COLUMNS,
                    "found_columns": list(df.columns)
                }, status=status.HTTP_400_BAD_REQUEST)

            data = getJsonGraphData(df, user, int(year))
            return Response(data)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExtractCSVView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "Missing file"}, status=400)

        try:
            df = pd.read_csv(file_obj)
            if list(df.columns) != EXPECTED_COLUMNS:
                return Response({
                    "error": "CSV headers do not match expected Netflix viewing data columns.",
                    "expected_columns": EXPECTED_COLUMNS,
                    "found_columns": list(df.columns)
                }, status=400)

            user_years_map = {}
            users = df['Profile Name'].unique().tolist()
            for user in users:
                years_for_user = pd.to_datetime(df[df['Profile Name'] == user]['Start Time']).dt.year.unique().tolist()
                user_years_map[user] = sorted(years_for_user)

            return Response(user_years_map)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return Response({"error": str(e)}, status=500)

