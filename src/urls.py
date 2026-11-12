"""Classify input using hostname boundaries rather than substring matches."""

from urllib.parse import urlsplit


def detect_url_type(value: str) -> str:
    value = value.strip()
    if not value:
        return "invalid"
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"}:
            return "invalid" if "://" in value else "search"
        host = (parsed.hostname or "").lower().rstrip(".")
    except ValueError:
        return "invalid"
    if not host:
        return "invalid"
    for domain, kind in (("spotify.com", "spotify"), ("youtube.com", "youtube"),
                         ("youtu.be", "youtube"), ("youtube-nocookie.com", "youtube")):
        if host == domain or host.endswith("." + domain):
            return kind
    return "other"
