from rest_framework.response import Response
from rest_framework import status
import pandas as pd
from functools import wraps

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

def validate_csv_columns(func):
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "Missing file"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_csv(file_obj)
        except Exception as e:
            return Response({"error": "Failed to read CSV: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if list(df.columns) != EXPECTED_COLUMNS:
            return Response({
                "error": "CSV headers do not match expected columns.",
                "expected_columns": EXPECTED_COLUMNS,
                "found_columns": list(df.columns)
            }, status=status.HTTP_400_BAD_REQUEST)

        request.csv_df = df

        return func(self, request, *args, **kwargs)

    return wrapper
