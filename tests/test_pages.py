"""Smoke tests for the full build: every page renders and links resolve."""

import pytest

from conftest import parse_html

PAGES = [
    "index.html",
    "contact.html",
    "data.html",
    "tools.html",
    "logo.html",
    "tools/tokenizer.html",
    "tools/dithering.html",
    "blog/index.html",
]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(published, page):
    doc = parse_html(published / page)
    assert doc.xpath("string(//title)").strip()
    assert doc.xpath("//body")


def test_blog_index_links_every_post(published):
    doc = parse_html(published / "blog/index.html")
    hrefs = doc.xpath("//a[@class='blog-post-link']/@href")
    assert sorted(hrefs) == ["headings-tables-code", "math-on-the-page"]
    for href in hrefs:
        assert (published / "blog" / f"{href}.html").is_file()


@pytest.mark.xfail(strict=True, reason="generate_blog_index sorts on a 'date' key that metadata never has")
def test_blog_index_newest_first(published):
    doc = parse_html(published / "blog/index.html")
    hrefs = doc.xpath("//a[@class='blog-post-link']/@href")
    assert hrefs == ["math-on-the-page", "headings-tables-code"]


def test_rebuild_removes_stale_output(build, tmp_path):
    """set_up_directories wipes output from a previous build (e.g. a deleted post)."""
    from conftest import chdir
    stale = tmp_path / "published" / "blog" / "deleted-post.html"
    stale.parent.mkdir(parents=True)
    stale.write_text("old")
    with chdir(tmp_path):
        build.set_up_directories()
    assert not stale.exists()
    assert (tmp_path / "published" / "blog").is_dir()
