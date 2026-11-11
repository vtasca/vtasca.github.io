"""Offline link checker for the built site in published/.

Checks every href/src (plus srcset entries) in the built HTML files:

* internal links and asset paths must resolve to a file in the build
  (``foo/`` resolves to ``foo/index.html``; ``foo`` also tries ``foo.html``,
  which is how GitHub Pages serves extensionless URLs);
* ``#fragment`` links must match an ``id`` (or ``<a name>``) in the target page;
* absolute links to the site's own domain are checked as internal links;
* ``url(...)`` references in built CSS files must resolve too;
* ``<loc>`` in sitemap.xml and ``<link>``/``<guid>`` in RSS feeds must map to
  a built page;
* ``og:image``/``og:url`` meta tags are reported as warnings when they are not
  absolute URLs (social previews ignore relative ones);
* external links are only collected and listed, never fetched.

Usage:
    python scripts/check_links.py [published] [--list-external]

Exits 1 when any internal link or anchor is broken.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

SITE_HOSTS = {"vtasca.dev", "www.vtasca.dev", "vtasca.github.io"}
URL_ATTRS = {"href", "src", "poster", "data-src"}
SKIP_SCHEMES = {"mailto", "tel", "javascript", "data", "blob"}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[int, str, str]] = []  # (line, tag, url)
        self.ids: set[str] = set()
        self.base: str | None = None
        self.meta: list[tuple[int, str, str]] = []  # (line, property, content)

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        if tag == "meta":
            d = dict(attrs)
            prop = d.get("property") or d.get("name") or ""
            if prop in {"og:image", "og:url", "twitter:image"}:
                self.meta.append((line, prop, d.get("content") or ""))
            return
        for key, value in attrs:
            if value is None:
                continue
            if key == "id" or (tag == "a" and key == "name"):
                self.ids.add(value)
            elif tag == "base" and key == "href":
                self.base = value
            elif key in URL_ATTRS:
                # <link rel="preconnect"/"dns-prefetch"> point at origins, not files
                rel = dict(attrs).get("rel") or ""
                if tag == "link" and rel in {"preconnect", "dns-prefetch"}:
                    continue
                self.links.append((line, tag, value.strip()))
            elif key == "srcset":
                for part in value.split(","):
                    url = part.strip().split(" ")[0]
                    if url:
                        self.links.append((line, tag, url))

    handle_startendtag = handle_starttag


def parse(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    parser.close()
    return parser


def resolve(root: Path, target: Path) -> Path | None:
    """Map a URL path inside the build to the file GitHub Pages would serve."""
    candidates = [target]
    if target.suffix == "":
        candidates += [target / "index.html", target.with_name(target.name + ".html")]
    for c in candidates:
        if c.is_file():
            return c
    return None


CSS_URL_RE = re.compile(r"""url\(\s*(['"]?)(?P<url>[^'")]+)\1\s*\)""")
XML_URL_RE = re.compile(r"<(loc|link|guid)\b[^>]*>\s*(?P<url>[^<\s]+)\s*</\1>")


def css_links(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    for m in CSS_URL_RE.finditer(text):
        yield text.count("\n", 0, m.start()) + 1, "css", m["url"]


def xml_links(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    for m in XML_URL_RE.finditer(text):
        yield text.count("\n", 0, m.start()) + 1, m.group(1), m["url"]


class Report:
    def __init__(self):
        self.broken: list[str] = []
        self.warnings: list[str] = []
        self.external: dict[str, set[str]] = defaultdict(set)
        self.checked = 0


def check_site(root: Path) -> Report:
    root = root.resolve()
    report = Report()
    pages = sorted(root.rglob("*.html"))
    parsed = {p: parse(p) for p in pages}
    id_cache: dict[Path, set[str]] = {p: d.ids for p, d in parsed.items()}

    def ids_for(path: Path) -> set[str]:
        if path not in id_cache:
            id_cache[path] = parse(path).ids if path.suffix == ".html" else set()
        return id_cache[path]

    sources = [(p, d.links) for p, d in parsed.items()]
    sources += [(p, list(css_links(p))) for p in sorted(root.rglob("*.css"))]
    sources += [(p, list(xml_links(p))) for p in sorted(root.rglob("*.xml"))]

    for page, data in parsed.items():
        for line, prop, content in data.meta:
            if not urlsplit(content).scheme:
                report.warnings.append(
                    f"{page.relative_to(root)}:{line}: {prop} should be an absolute URL, got '{content}'"
                )

    for page, links in sources:
        rel_page = page.relative_to(root)
        for line, tag, url in links:
            where = f"{rel_page}:{line}"
            if not url or "{{" in url or "{%" in url:
                if "{{" in url or "{%" in url:
                    report.broken.append(
                        f"{where}: unrendered template in <{tag}>: {url}"
                    )
                continue
            parts = urlsplit(url)
            scheme = parts.scheme.lower()
            if scheme in SKIP_SCHEMES:
                continue
            if scheme in {"http", "https"} or url.startswith("//"):
                if parts.hostname not in SITE_HOSTS:
                    report.external[url].add(str(rel_page))
                    continue
                base_dir, path = root, parts.path.lstrip("/")
            elif scheme:
                report.external[url].add(str(rel_page))
                continue
            elif parts.path.startswith("/"):
                base_dir, path = root, parts.path.lstrip("/")
            else:
                base_dir, path = page.parent, parts.path

            report.checked += 1
            if path == "" and base_dir == page.parent:
                target = page  # "#frag" or "?q" on the same page
            else:
                joined = (base_dir / unquote(path)).resolve()
                try:
                    joined.relative_to(root)
                except ValueError:
                    report.broken.append(
                        f"{where}: <{tag}> {url} points outside the site"
                    )
                    continue
                target = resolve(root, joined) if path else resolve(root, root)
                if target is None:
                    report.broken.append(f"{where}: <{tag}> {url} -> missing file")
                    continue

            if parts.fragment:
                frag = unquote(parts.fragment)
                if frag != "top" and frag not in ids_for(target):
                    report.broken.append(
                        f"{where}: <{tag}> {url} -> no id '{frag}' in {target.relative_to(root)}"
                    )
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Offline link checker for published/")
    parser.add_argument("root", nargs="?", default="published", type=Path)
    parser.add_argument(
        "--list-external", action="store_true", help="print external URLs (not fetched)"
    )
    args = parser.parse_args(argv)

    if not args.root.is_dir():
        print(
            f"{args.root} does not exist; run scripts/build.py first", file=sys.stderr
        )
        return 2

    report = check_site(args.root)
    if args.list_external:
        print(f"External links ({len(report.external)}, not fetched):")
        for url in sorted(report.external):
            print(f"  {url}  [{', '.join(sorted(report.external[url]))}]")
        print()
    for line in report.warnings:
        print(f"WARN   {line}")
    for line in report.broken:
        print(f"BROKEN {line}")
    print(
        f"{report.checked} internal links checked, {len(report.broken)} broken, "
        f"{len(report.warnings)} warnings, {len(report.external)} external URLs listed"
    )
    return 1 if report.broken else 0


if __name__ == "__main__":
    sys.exit(main())
