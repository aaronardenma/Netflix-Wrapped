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
        file_objs = request.FILES.getlist('files') or request.FILES.getlist('file')
        if not file_objs:
            return Response({"error": "Missing file"}, status=status.HTTP_400_BAD_REQUEST)

        dataframes = []
        try:
            for file_obj in file_objs:
                file_obj.seek(0)
                df = pd.read_csv(file_obj)
                if not set(EXPECTED_COLUMNS).issubset(set(df.columns)):
                    return Response({
                        "error": "CSV headers do not match expected columns.",
                        "expected_columns": EXPECTED_COLUMNS,
                        "found_columns": list(df.columns),
                        "file": getattr(file_obj, "name", "upload.csv"),
                    }, status=status.HTTP_400_BAD_REQUEST)
                dataframes.append(df)
        except Exception as e:
            return Response({"error": "Failed to read CSV: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)

        request.csv_dfs = dataframes
        request.csv_df = pd.concat(dataframes, ignore_index=True) if len(dataframes) > 1 else dataframes[0]

        return func(self, request, *args, **kwargs)

    return wrapper

