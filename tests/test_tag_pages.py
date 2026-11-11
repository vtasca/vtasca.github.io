"""Tests for blog tag pages. Uses only committed markdown; no Notion access.

Run with: uv run --with pytest pytest tests/test_tag_pages.py
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import build  # noqa: E402

POSTS = [
    {"id": "a", "name": "Old", "url": "old", "description": "",
     "tags": ["Data", "python"], "created_time": "2022-01-01T00:00:00.000Z",
     "last_edited_time": "2025-06-01T00:00:00.000Z"},
    {"id": "b", "name": "New", "url": "new", "description": "",
     "tags": ["data", "Machine Learning"], "created_time": "2025-01-01T00:00:00.000Z",
     "last_edited_time": "2025-02-01T00:00:00.000Z"},
    {"id": "c", "name": "Untagged", "url": "untagged", "description": "",
     "created_time": "2023-01-01T00:00:00.000Z",
     "last_edited_time": "2023-01-01T00:00:00.000Z"},
]


@pytest.fixture(autouse=True)
def in_repo(monkeypatch):
    # build.py resolves templates relative to the working directory
    monkeypatch.chdir(REPO)


def test_tag_slug():
    assert build.tag_slug("Machine Learning") == "machine-learning"
    assert build.tag_slug("C++ / Rust") == "c-rust"
    assert build.tag_slug("Économie") == "economie"


def test_sort_posts_newest_created_first():
    assert [p["url"] for p in build.sort_posts(POSTS)] == ["new", "untagged", "old"]


def test_collect_tags_merges_case_variants_and_counts():
    tags = build.collect_tags(POSTS)
    assert [(t["slug"], t["count"]) for t in tags] == [
        ("data", 2), ("machine-learning", 1), ("python", 1)
    ]
    # first spelling seen wins
    assert tags[0]["name"] == "Data"


def test_collect_tags_counts_a_post_once_per_slug():
    tags = build.collect_tags([{"tags": ["data", "Data", ""]}])
    assert tags == [{"name": "data", "slug": "data", "count": 1}]


def test_generate_tag_pages(tmp_path):
    (tmp_path / "blog").mkdir()
    build.generate_tag_pages(POSTS, tmp_path)
    tag_dir = tmp_path / "blog" / "tag"
    assert sorted(p.name for p in tag_dir.iterdir()) == [
        "data.html", "index.html", "machine-learning.html", "python.html"
    ]
    data = (tag_dir / "data.html").read_text()
    # both posts, newest first, linked relative to the site root
    assert data.index('href="../../blog/new"') < data.index('href="../../blog/old"')
    assert "untagged" not in data
    assert 'aria-current="page"' in data
    assert 'href="../../static/styles.css' in data
    python = (tag_dir / "python.html").read_text()
    assert 'href="../../blog/old"' in python and 'href="../../blog/new"' not in python
    overview = (tag_dir / "index.html").read_text()
    assert 'href="../../blog/tag/machine-learning"' in overview


def test_blog_index_has_filter_and_no_nested_links(tmp_path):
    (tmp_path / "blog").mkdir()
    build.generate_blog_index(POSTS, tmp_path, REPO / "src")
    html = (tmp_path / "blog" / "index.html").read_text()
    assert 'class="tag-filter"' in html
    assert 'href="../blog/tag/machine-learning"' in html
    assert html.index('href="../blog/new"') < html.index('href="../blog/old"')
    # tag links must not sit inside another <a>
    assert '<a href="../blog/new" class="blog-post-link">' not in html


def test_full_build_with_committed_content(tmp_path):
    """Run the real build entry point on a copy of the repo (fetch step skipped)."""
    shutil.copytree(REPO / "src", tmp_path / "src")
    shutil.copytree(REPO / "scripts", tmp_path / "scripts")
    subprocess.run([sys.executable, "scripts/build.py"], cwd=tmp_path, check=True)

    published = tmp_path / "published"
    meta = json.loads((REPO / "src" / "blog_metadata.json").read_text())
    expected = {build.tag_slug(t) for p in meta for t in p.get("tags", [])}
    built = {p.stem for p in (published / "blog" / "tag").glob("*.html")} - {"index"}
    assert built == expected

    for post in meta:
        html = (published / "blog" / f"{post['url']}.html").read_text()
        for tag in post["tags"]:
            assert f'href="../blog/tag/{build.tag_slug(tag)}"' in html

    sitemap = (published / "sitemap.xml").read_text()
    for slug in expected:
        assert f"https://vtasca.dev/blog/tag/{slug}</loc>" in sitemap
