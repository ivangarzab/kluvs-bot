"""
Helpers for converting between user-supplied date/time strings and the
ISO 8601 scheduled_at timestamps stored by the API.
"""
from datetime import datetime, timezone


def parse_scheduled_at(date_str: str, time_str: str) -> str:
    """Combines a 'YYYY-MM-DD' date and 'HH:MM' time into a UTC scheduled_at ISO string."""
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).isoformat()


def to_discord_timestamp(iso_str: str, style: str = "F") -> str:
    """Converts an ISO 8601 string into a Discord timestamp tag.

    Discord renders <t:epoch:style> client-side in each viewer's own
    local timezone, so this is the preferred way to show scheduled_at
    in embeds and messages.
    """
    dt = datetime.fromisoformat(iso_str)
    return f"<t:{int(dt.timestamp())}:{style}>"


def format_human_readable(iso_str: str) -> str:
    """Formats an ISO 8601 string as plain text, e.g. 'June 1, 2026 at 6:00 PM UTC'.

    Use this where Discord timestamp tags aren't rendered, such as
    autocomplete choice labels.
    """
    dt = datetime.fromisoformat(iso_str)
    return dt.strftime("%B %-d, %Y at %-I:%M %p UTC")
