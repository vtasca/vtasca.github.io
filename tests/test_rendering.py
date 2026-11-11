"""Blog post rendering: headings/anchors, tables, code, and escaping."""

import re

from conftest import parse_html

POST = "blog/headings-tables-code.html"


def js_slugify(text):
    """Python port of slugify() in src/static/core.js (setupHeadingAnchors)."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.ASCII)
    text = re.sub(r"[\s_-]+", "-", text)
    return re.sub(r"^-+|-+$", "", text)


def anchor_ids(headings):
    """Mirror core.js: skip headings that already have ids, dedupe with -N."""
    used, ids = set(), []
    for h in headings:
        if h.get("id"):
            used.add(h.get("id"))
            continue
        base = js_slugify(h.text_content())
        if not base:
            continue
        candidate, n = base, 1
        while candidate in used:
            candidate = f"{base}-{n}"
            n += 1
        used.add(candidate)
        ids.append(candidate)
    return ids


def test_every_post_is_rendered(published):
    assert (published / POST).is_file()
    assert (published / "blog/math-on-the-page.html").is_file()


def test_title_is_single_h1_and_escaped(published):
    doc = parse_html(published / POST)
    h1s = doc.xpath("//article//h1")
    assert [h.text_content() for h in h1s] == ["Headings, tables & <code>"]
    # The raw title must be escaped, not injected as a <code> element.
    assert not doc.xpath("//article//h1/code")


def test_heading_levels_preserved(published):
    doc = parse_html(published / POST)
    got = [(h.tag, h.text_content()) for h in doc.xpath("//article//*[self::h2 or self::h3 or self::h4]")]
    assert got == [
        ("h2", "Getting started"),
        ("h3", "Install the tools"),
        ("h2", "Getting started"),
        ("h4", "What's next? (Part 2)"),
    ]


def test_headings_get_unique_anchor_ids(published):
    """core.js adds ids client-side; the build must hand it id-less headings in <article>."""
    doc = parse_html(published / POST)
    headings = doc.xpath("//article//*[self::h2 or self::h3 or self::h4 or self::h5 or self::h6]")
    assert all(not h.get("id") for h in headings)
    ids = anchor_ids(headings)
    assert ids == [
        "getting-started",
        "install-the-tools",
        "getting-started-1",
        "whats-next-part-2",
    ]
    assert len(ids) == len(set(ids))


def test_paragraphs_survive(published):
    text = parse_html(published / POST).xpath("string(//article)")
    for snippet in [
        "Intro paragraph before any heading.",
        "Run the installer.",
        "A second section that reuses the heading text",
        "Punctuation in headings is stripped",
    ]:
        assert snippet in text


def test_table_and_code_block(published):
    doc = parse_html(published / POST)
    assert [th.text_content() for th in doc.xpath("//article//table//th")] == ["Column A", "Column B"]
    code = doc.xpath("string(//article//pre/code)")
    assert 'if 1 < 2:' in code  # decoded text; the source must have been escaped
    assert "&lt;" in (published / POST).read_text()


def test_links_and_metadata(published):
    doc = parse_html(published / POST)
    assert doc.xpath("//article//a[@href='https://example.com']")
    assert doc.xpath("string(//span[@class='article-date'])").strip() == "2026-01-05"
    assert [t.text_content() for t in doc.xpath("//span[@class='tag']")] == ["testing", "fixtures"]


def test_convert_without_metadata_uses_file_name(build, in_repo, tmp_path):
    md = tmp_path / "plain-post.md"
    md.write_text("## Hello\n\nWorld.\n")
    build.convert_markdown_to_html(md, metadata=None, output_dir=tmp_path)
    doc = parse_html(tmp_path / "plain-post.html")
    assert doc.xpath("string(//article//h2)") == "Hello"
    assert doc.xpath("string(//title)").startswith("Blog Post")
