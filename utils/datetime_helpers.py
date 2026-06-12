"""
Helpers for converting stored ISO 8601 timestamps into user-facing formats.
"""
from datetime import datetime


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
