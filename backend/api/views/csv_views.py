from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
import pandas as pd
from utils.csv_utils import validate_csv
from utils.data_analysis import getJsonGraphData
from api.serializers import UploadCSVSerializer
from ..utils import validate_csv_columns

class UploadCSVView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        print("Received request to UploadCSVView")

        serializer = UploadCSVSerializer(data=request.data)
        if not serializer.is_valid():
            print("Serializer invalid:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = serializer.validated_data['file']
        user = serializer.validated_data['user']
        year = serializer.validated_data['year']

        print(f"Validated data — user: {user}, year: {year}, filename: {file.name}")

        try:
            df = validate_csv(file)
            print("CSV validated successfully. Head of DataFrame:")
            print(df.head())

            data = getJsonGraphData(df, user, year)
            print("Generated graph data successfully.")
            print(data)
            return Response(data)

        except Exception as e:
            print("Exception occurred in UploadCSVView:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExtractCSVView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    

    @validate_csv_columns
    def post(self, request, format=None):
        print("Received request to ExtractCSVView")

        try:
            df = request.csv_df
            print("CSV columns:", df.columns.tolist())
            print("Sample rows:")
            print(df.head())

            users = df['Profile Name'].dropna().unique().tolist()
            print("Extracted users:", users)

            user_years_map = {
                user: sorted(
                    pd.to_datetime(df[df['Profile Name'] == user]['Start Time'], errors="coerce")
                    .dropna()
                    .dt.year
                    .unique()
                    .tolist()
                )
                for user in users
            }

            print("Extracted user-year map:", user_years_map)
            return Response(user_years_map)

        except Exception as e:
            print("Exception occurred in ExtractCSVView:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
