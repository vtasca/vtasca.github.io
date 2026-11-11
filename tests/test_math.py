"""LaTeX in markdown is converted to MathML; display math gets a wrapper div."""

from conftest import parse_html

POST = "blog/math-on-the-page.html"


def _maths(doc):
    return doc.xpath("//*[local-name()='math']")


def test_inline_and_display_math_become_mathml(published):
    doc = parse_html(published / POST)
    displays = [m.get("display") for m in _maths(doc)]
    assert displays.count("inline") == 2
    assert displays.count("block") == 2


def test_display_math_is_wrapped_in_container(published):
    doc = parse_html(published / POST)
    for m in _maths(doc):
        parent = m.getparent()
        if m.get("display") == "block":
            assert parent.tag == "div" and parent.get("class") == "math-container"
        else:
            assert parent.get("class") != "math-container"


def test_no_raw_latex_left_in_output(published):
    text = parse_html(published / POST).xpath("string(//article)")
    assert "\\frac" not in text
    assert "$$" not in text
    assert "$ EFFR $" not in text


def test_lone_dollar_sign_stays_text(published):
    text = parse_html(published / POST).xpath("string(//article)")
    assert "Starting capital of $100 should stay plain text" in text


def test_fraction_is_rendered(published):
    doc = parse_html(published / POST)
    assert doc.xpath("//*[local-name()='mfrac']")


def test_wrapper_regex_handles_multiline_math(build, in_repo, tmp_path):
    md = tmp_path / "m.md"
    md.write_text("Text.\n\n$$\na + b\n= c\n$$\n\nMore text.\n")
    out = build.convert_markdown_to_html(md, output_dir=tmp_path)
    assert out.count('<div class="math-container">') == 1
    assert "More text." in out
