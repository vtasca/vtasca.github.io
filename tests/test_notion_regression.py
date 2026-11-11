"""Regression test for the dropped-paragraph bug (notion2md fork bump, 2026-09-30).

Notion sends ``"icon": null`` on plain paragraph blocks. Before
vtasca/notion2md-extended@a482af0, ``collect_info`` did ``payload["icon"]["emoji"]``,
which raised TypeError; ``convert_block`` swallows exceptions and returns "",
so every such paragraph silently disappeared from the post. The same happened
to callouts with non-emoji (external/file) icons.

These tests drive the converter with recorded block JSON, so no Notion token or
network access is needed, then push the markdown through the site build.
"""

import json

import pytest
from notion2md.convertor.block import BlockConvertor

from conftest import FIXTURES, parse_html

BLOCKS = json.loads((FIXTURES / "notion" / "paragraphs_with_icons.json").read_text())

EXPECTED_TEXT = [
    "Section title",
    "First paragraph has a null icon.",
    "Second paragraph,",
    "bold part",
    "Callout with an emoji icon.",
    "Callout with an external icon.",
    "Closing paragraph without an icon key.",
]


@pytest.fixture(scope="module")
def markdown():
    # None of these blocks have children or files, so no client/config is touched.
    return BlockConvertor(config=None, client=None).convert(BLOCKS)


@pytest.mark.parametrize("snippet", EXPECTED_TEXT)
def test_no_block_is_dropped(markdown, snippet):
    assert snippet in markdown


def test_blocks_keep_their_order(markdown):
    positions = [markdown.index(s) for s in EXPECTED_TEXT]
    assert positions == sorted(positions)


def test_null_icon_paragraph_is_plain_text(markdown):
    assert "First paragraph has a null icon.\n\n" in markdown
    assert "None" not in markdown


def test_emoji_callout_keeps_icon(markdown):
    assert ">\U0001F4A1\n>\n>Callout with an emoji icon." in markdown


def test_paragraphs_reach_published_html(markdown, build, in_repo, tmp_path):
    md = tmp_path / "from-notion.md"
    md.write_text(markdown, encoding="utf-8")
    build.convert_markdown_to_html(md, output_dir=tmp_path)
    doc = parse_html(tmp_path / "from-notion.html")
    article = doc.xpath("string(//article)")
    for snippet in EXPECTED_TEXT:
        assert snippet in article
    assert doc.xpath("//article//p/strong[text()='bold part']")
    # inline equation from Notion ("$ x^2 $") becomes MathML
    assert doc.xpath("//article//p/*[local-name()='math']")
    assert doc.xpath("string(//article//h2)") == "Section title"
