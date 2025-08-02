import pandas as pd
from rest_framework.exceptions import ValidationError

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

def validate_csv(file) -> pd.DataFrame:
    try:
        df = pd.read_csv(file)
    except Exception as e:
        raise ValidationError(f"Unable to read CSV file: {str(e)}")

    if list(df.columns) != EXPECTED_COLUMNS:
        raise ValidationError({
            "error": "CSV headers do not match expected Netflix viewing data columns.",
            "expected_columns": EXPECTED_COLUMNS,
            "found_columns": list(df.columns)
        })

    return df
