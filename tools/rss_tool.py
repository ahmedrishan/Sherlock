"""RSS and Atom Feed Parser Tool for Sherlock Voice Assistant.

Fetches, parses, and sanitizes RSS/Atom web feeds for LLM tool-calling.
"""

from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error
import socket
import re
import html
from html.parser import HTMLParser

try:
    import feedparser
except ImportError:
    feedparser = None  # Handled gracefully inside fetch_rss_feed


class _HTMLTextExtractor(HTMLParser):
    """Simple, zero-dependency HTML parser to extract clean text content."""

    def __init__(self):
        super().__init__()
        self.result: List[str] = []

    def handle_data(self, data: str):
        self.result.append(data)

    def get_text(self) -> str:
        return "".join(self.result)


def _clean_html_summary(raw_html: str, max_chars: int = 300) -> str:
    """Strips HTML tags, decodes HTML entities, and normalizes whitespace."""
    if not raw_html:
        return ""

    try:
        parser = _HTMLTextExtractor()
        parser.feed(raw_html)
        text = parser.get_text()
    except Exception:
        # Fallback regex strip if HTML parsing fails on malformed snippet
        text = re.sub(r"<[^>]+>", " ", raw_html)

    # Decode entities like &amp;, &quot;, &lt;, etc.
    text = html.unescape(text)

    # Normalize excessive spaces, tabs, and newlines
    text = re.sub(r"\s+", " ", text).strip()

    # Truncate summary to keep tokens manageable for the LLM
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "..."

    return text


def fetch_rss_feed(
    feed_url: str,
    max_entries: int = 5,
    timeout: int = 10
) -> Dict[str, Any]:
    """Fetches and parses an RSS or Atom feed from a given URL.

    Use this tool when the user asks for news, recent articles, blog posts,
    or podcast updates from a specific web feed URL.

    Args:
        feed_url: The full HTTP/HTTPS URL of the RSS or Atom feed.
        max_entries: Maximum number of feed items to return (default 5, max 20).
        timeout: Network socket timeout in seconds (default 10).

    Returns:
        A structured dictionary containing:
        - status (str): "success" or "error"
        - feed (dict): Feed metadata (title, link, description)
        - entries (list[dict]): List of items with title, link, published date, and summary
        - count (int): Total entries returned
        - error (str | None): Detailed error description if fetch/parse failed
    """
    if feedparser is None:
        return {
            "status": "error",
            "feed": {},
            "entries": [],
            "count": 0,
            "error": "The 'feedparser' library is not installed. Run 'pip install feedparser'."
        }

    max_entries = max(1, min(max_entries, 20))

    # Enforce URL scheme validation
    if not (feed_url.startswith("http://") or feed_url.startswith("https://")):
        return {
            "status": "error",
            "feed": {},
            "entries": [],
            "count": 0,
            "error": "Invalid URL scheme. URL must start with http:// or https://"
        }

    # Fetch raw data using urllib to enforce explicit timeout & custom User-Agent
    req = urllib.request.Request(
        feed_url,
        headers={"User-Agent": "SherlockVoiceAssistant/1.0 (+https://github.com/sherlock-assistant)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw_data = response.read()
    except urllib.error.HTTPError as e:
        return {
            "status": "error",
            "feed": {},
            "entries": [],
            "count": 0,
            "error": f"HTTP Error {e.code}: {e.reason}"
        }
    except urllib.error.URLError as e:
        return {
            "status": "error",
            "feed": {},
            "entries": [],
            "count": 0,
            "error": f"Network/URL Error: {e.reason}"
        }
    except (TimeoutError, socket.timeout):
        return {
            "status": "error",
            "feed": {},
            "entries": [],
            "count": 0,
            "error": f"Connection timed out after {timeout} seconds."
        }
    except Exception as e:
        return {
            "status": "error",
            "feed": {},
            "entries": [],
            "count": 0,
            "error": f"Failed to retrieve feed content: {str(e)}"
        }

    # Parse XML/Atom payload via feedparser
    try:
        parsed = feedparser.parse(raw_data)
    except Exception as e:
        return {
            "status": "error",
            "feed": {},
            "entries": [],
            "count": 0,
            "error": f"Feed parsing failed: {str(e)}"
        }

    # Handle critical bozo exceptions (e.g. invalid XML structure with no parseable entries)
    if parsed.get("bozo") and not parsed.get("entries"):
        bozo_exc = parsed.get("bozo_exception", "Malformed feed content")
        return {
            "status": "error",
            "feed": {},
            "entries": [],
            "count": 0,
            "error": f"Malformed RSS/Atom feed: {str(bozo_exc)}"
        }

    # Extract Feed metadata
    feed_meta = {
        "title": parsed.feed.get("title", "Untitled Feed"),
        "link": parsed.feed.get("link", feed_url),
        "description": _clean_html_summary(parsed.feed.get("description", ""), max_chars=200)
    }

    # Process and normalize entry list
    entries: List[Dict[str, str]] = []
    for entry in parsed.entries[:max_entries]:
        # Extract best available summary / content
        raw_summary = ""
        if "summary" in entry:
            raw_summary = entry.summary
        elif "description" in entry:
            raw_summary = entry.description
        elif "content" in entry and entry.content:
            raw_summary = entry.content[0].get("value", "")

        # Date normalization
        pub_date = (
            entry.get("published")
            or entry.get("updated")
            or entry.get("pubDate")
            or "Unknown date"
        )

        entries.append({
            "title": entry.get("title", "Untitled Entry").strip(),
            "link": entry.get("link", ""),
            "published": str(pub_date).strip(),
            "summary": _clean_html_summary(raw_summary, max_chars=350)
        })

    return {
        "status": "success",
        "feed": feed_meta,
        "entries": entries,
        "count": len(entries),
        "error": None
    }
