import logging
from time import perf_counter


logger = logging.getLogger(__name__)


DEFAULT_RECAP_SECTIONS = [
    "total_title_watchtime",
    "total_type_watchtime",
    "monthly_watchtime",
    "ratings_watchtime",
    "core_stats",
    "title_level_insights",
    "wrapped_cards",
    "genre_content_insights",
    "visualizations",
]

HEAVY_RECAP_SECTIONS = {
    "genre_content_insights",
    "visualizations",
    "profile_comparisons",
}


def timed_section(section_name, builder, context=None):
    start = perf_counter()
    result = builder()
    elapsed_ms = round((perf_counter() - start) * 1000, 2)
    logger.info(
        "recap section generated",
        extra={
            "section": section_name,
            "elapsed_ms": elapsed_ms,
            **(context or {}),
        },
    )
    return result, elapsed_ms


def build_recap_payload(builders, requested_sections, context=None):
    graphs = {}
    timings = {}

    for section_name in DEFAULT_RECAP_SECTIONS:
        if section_name not in requested_sections:
            continue
        graphs[section_name], timings[section_name] = timed_section(
            section_name,
            builders[section_name],
            context=context,
        )

    graphs["_timings_ms"] = timings
    return graphs
