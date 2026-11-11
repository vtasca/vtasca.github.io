"""RSS 2.0 date format checks for generate_rss_feed (standalone, no conftest)."""
import importlib.util
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def build():
    spec = importlib.util.spec_from_file_location("site_build", ROOT / "scripts" / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def channel(build, tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)  # templates are loaded from src/templates
    (tmp_path / "blog").mkdir()
    posts = [
        {"name": "Older", "url": "older", "description": "d", "tags": ["a"],
         "last_edited_time": "2025-03-10T09:53:00.000Z"},
        {"name": "Newer", "url": "newer", "description": "d", "tags": [],
         "last_edited_time": "2025-06-10T21:56:00.000Z"},
    ]
    build.generate_rss_feed(posts, tmp_path)
    return ET.parse(tmp_path / "blog" / "rss.xml").getroot().find("channel")


def test_pubdate_is_rfc822_and_matches_metadata(channel):
    dates = [parsedate_to_datetime(i.findtext("pubDate")) for i in channel.findall("item")]
    assert dates == [
        datetime(2025, 6, 10, 21, 56, tzinfo=timezone.utc),
        datetime(2025, 3, 10, 9, 53, tzinfo=timezone.utc),
    ]
    assert channel.find("item").findtext("pubDate") == "Tue, 10 Jun 2025 21:56:00 +0000"


def test_last_build_date_is_rfc822_with_timezone(channel):
    raw = channel.findtext("lastBuildDate").strip()
    parsed = parsedate_to_datetime(raw)
    assert parsed.tzinfo is not None
    assert raw.endswith("+0000")
    assert abs((datetime.now(timezone.utc) - parsed).total_seconds()) < 300
