"""RSS feed and sitemap output."""

from email.utils import parsedate_to_datetime

import pytest

from conftest import parse_xml

SITEMAP_NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
BASE = "https://vtasca.dev"


# --- RSS -------------------------------------------------------------------

@pytest.fixture(scope="module")
def channel(published):
    root = parse_xml(published / "blog/rss.xml")  # raises if the XML is malformed
    assert root.tag == "rss" and root.get("version") == "2.0"
    return root.find("channel")


def test_rss_has_one_item_per_post(channel):
    links = [i.findtext("link") for i in channel.findall("item")]
    assert sorted(links) == [
        f"{BASE}/blog/headings-tables-code",
        f"{BASE}/blog/math-on-the-page",
    ]


def test_rss_items_newest_edit_first(channel):
    titles = [i.findtext("title") for i in channel.findall("item")]
    assert titles == ["Math on the page", "Headings, tables & <code>"]


def test_rss_escapes_special_characters(published, channel):
    raw = (published / "blog/rss.xml").read_text()
    assert "Headings, tables &amp; &lt;code&gt;" in raw
    item = channel.findall("item")[1]
    assert item.findtext("description") == "Fixture post: structure, escaping & links"


def test_rss_item_fields(channel):
    item = channel.findall("item")[1]
    assert item.findtext("guid") == item.findtext("link")
    assert [c.text for c in item.findall("category")] == ["testing", "fixtures"]


def test_rss_self_link(channel):
    atom = channel.find("{http://www.w3.org/2005/Atom}link")
    assert atom.get("href") == f"{BASE}/blog/rss.xml"
    assert atom.get("rel") == "self"


# Known issues, recorded as strict xfails: they fail today, and the suite will
# flag them (XPASS -> failure) once build.py / rss.xml are fixed, so the marker
# can be removed.

@pytest.mark.xfail(strict=True, reason="pubDate is ISO 8601 from Notion, RSS 2.0 requires RFC 822")
def test_rss_pubdate_is_rfc822(channel):
    for item in channel.findall("item"):
        parsedate_to_datetime(item.findtext("pubDate"))


@pytest.mark.xfail(strict=True, reason="lastBuildDate uses a naive datetime, so %z renders empty")
def test_rss_last_build_date_has_timezone(channel):
    assert parsedate_to_datetime(channel.findtext("lastBuildDate").strip()).tzinfo is not None


# --- Sitemap ---------------------------------------------------------------

@pytest.fixture(scope="module")
def sitemap_locs(published):
    root = parse_xml(published / "sitemap.xml")
    return [loc.text for loc in root.findall("s:url/s:loc", SITEMAP_NS)]


def test_sitemap_lists_every_page(sitemap_locs):
    assert sorted(sitemap_locs) == sorted([
        f"{BASE}/",
        f"{BASE}/blog/",
        f"{BASE}/blog/headings-tables-code",
        f"{BASE}/blog/math-on-the-page",
        f"{BASE}/contact",
        f"{BASE}/data",
        f"{BASE}/logo",
        f"{BASE}/tools",
        f"{BASE}/tools/dithering",
        f"{BASE}/tools/tokenizer",
    ])


def test_sitemap_matches_published_html(published, sitemap_locs):
    assert len(sitemap_locs) == len(list(published.rglob("*.html")))
    assert len(sitemap_locs) == len(set(sitemap_locs))


def test_sitemap_urls_are_clean(sitemap_locs):
    for loc in sitemap_locs:
        assert loc.startswith(f"{BASE}/")
        assert not loc.endswith(".html")
        assert "index" not in loc


def test_sitemap_host_matches_cname(sitemap_locs):
    from conftest import REPO_ROOT
    host = (REPO_ROOT / "CNAME").read_text().strip()
    assert all(loc.startswith(f"https://{host}/") for loc in sitemap_locs)
