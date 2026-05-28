import hashlib

import pandas as pd
from django.db import transaction
from django.utils import timezone

from api.models import NetflixProfile, Title, Upload, ViewingEvent
from utils.workflows import splitSecondOccurence


def normalize_title(title):
    return " ".join(str(title).strip().lower().split())


def duration_to_seconds(duration):
    try:
        parts = str(duration).split(":")
        if len(parts) != 3:
            return 0
        hours, minutes, seconds = [int(part) for part in parts]
        return hours * 3600 + minutes * 60 + seconds
    except (TypeError, ValueError):
        return 0


def clean_string(value):
    if pd.isna(value):
        return ""
    return str(value)


def build_row_hash(user_id, profile_name, started_at, title_raw, duration):
    raw = "|".join(
        [
            str(user_id),
            str(profile_name),
            started_at.isoformat() if hasattr(started_at, "isoformat") else str(started_at),
            str(title_raw),
            str(duration),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def clean_title(title_raw):
    cleaned_title = splitSecondOccurence(str(title_raw)).strip() or str(title_raw).strip()
    return cleaned_title


def get_or_create_title(title_raw):
    cleaned_title = clean_title(title_raw)
    normalized_name = normalize_title(cleaned_title)
    title, _ = Title.objects.get_or_create(
        normalized_name=normalized_name,
        defaults={
            "name": cleaned_title,
        },
    )
    return title


@transaction.atomic
def ingest_viewing_dataframe(user, dataframe, source_filename=""):
    if user is None:
        raise ValueError("Normalized viewing ingestion requires an authenticated user")

    upload = Upload.objects.create(
        user=user,
        source_filename=source_filename or "",
        status=Upload.Status.PROCESSING,
        is_anonymous=user is None,
    )

    try:
        events_to_create = []
        parsed_df = dataframe.copy()
        parsed_df["parsed_start_time"] = pd.to_datetime(parsed_df["Start Time"], errors="coerce")
        parsed_df = parsed_df.dropna(subset=["parsed_start_time", "Profile Name", "Title"])
        parsed_df["clean_profile_name"] = parsed_df["Profile Name"].apply(clean_string)
        parsed_df["clean_title"] = parsed_df["Title"].apply(clean_title)
        parsed_df["normalized_title"] = parsed_df["clean_title"].apply(normalize_title)

        profile_names = sorted(parsed_df["clean_profile_name"].unique())
        existing_profiles = {
            profile.name: profile
            for profile in NetflixProfile.objects.filter(user=user, name__in=profile_names)
        }
        missing_profiles = [
            NetflixProfile(user=user, name=name)
            for name in profile_names
            if name not in existing_profiles
        ]
        if missing_profiles:
            NetflixProfile.objects.bulk_create(missing_profiles, ignore_conflicts=True)
            existing_profiles = {
                profile.name: profile
                for profile in NetflixProfile.objects.filter(user=user, name__in=profile_names)
            }

        title_names = (
            parsed_df[["clean_title", "normalized_title"]]
            .drop_duplicates("normalized_title")
            .to_dict("records")
        )
        normalized_names = [row["normalized_title"] for row in title_names]
        existing_titles = {
            title.normalized_name: title
            for title in Title.objects.filter(normalized_name__in=normalized_names)
        }
        missing_titles = [
            Title(name=row["clean_title"], normalized_name=row["normalized_title"])
            for row in title_names
            if row["normalized_title"] not in existing_titles
        ]
        if missing_titles:
            Title.objects.bulk_create(missing_titles, ignore_conflicts=True)
            existing_titles = {
                title.normalized_name: title
                for title in Title.objects.filter(normalized_name__in=normalized_names)
            }

        for _, row in parsed_df.iterrows():
            profile = existing_profiles[row["clean_profile_name"]]
            title = existing_titles[row["normalized_title"]]
            started_at = row["parsed_start_time"]
            if timezone.is_naive(started_at):
                started_at = timezone.make_aware(started_at, timezone.get_current_timezone())

            duration_seconds = duration_to_seconds(row["Duration"])
            row_hash = build_row_hash(
                user.id if user else upload.id,
                profile.name,
                started_at,
                row["Title"],
                row["Duration"],
            )

            events_to_create.append(
                ViewingEvent(
                    upload=upload,
                    profile=profile,
                    title=title,
                    title_raw=clean_string(row["Title"]),
                    started_at=started_at,
                    duration_seconds=duration_seconds,
                    device_type=clean_string(row.get("Device Type")),
                    country=clean_string(row.get("Country")),
                    supplemental_video_type=clean_string(row.get("Supplemental Video Type")),
                    row_hash=row_hash,
                )
            )

        ViewingEvent.objects.bulk_create(events_to_create, ignore_conflicts=True)
        upload.status = Upload.Status.COMPLETED
        upload.completed_at = timezone.now()
        upload.save(update_fields=["status", "completed_at"])
        return upload
    except Exception as exc:
        upload.status = Upload.Status.FAILED
        upload.error_message = str(exc)
        upload.save(update_fields=["status", "error_message"])
        raise
