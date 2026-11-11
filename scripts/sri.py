"""Subresource Integrity for third-party <script> and stylesheet tags in templates.

Usage:
    python scripts/sri.py --check    # offline: every CDN tag is pinned and has integrity
    python scripts/sri.py --update   # fetch each CDN file, write integrity + crossorigin
    python scripts/sri.py --verify   # fetch each CDN file, compare with the stored hash

Only tags whose URL starts with http(s):// are considered. A URL counts as
pinned when it names an exact semver version (e.g. ``pkg@1.2.3`` on unpkg or
jsDelivr, or ``/libs/name/1.2.3/`` on cdnjs). SRI on a floating URL breaks the
page as soon as the CDN serves a new file, so --update refuses to hash those.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import re
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "src" / "templates"

# Matches <script ... src="https://..."> and <link ... href="https://..."> tags
# on a single line (which is how the templates are written).
TAG_RE = re.compile(
    r"<(?P<name>script|link)\b(?P<attrs>[^>]*?)\s*/?>",
    re.IGNORECASE,
)
ATTR_RE = re.compile(r'(?P<key>[a-zA-Z-]+)\s*=\s*"(?P<value>[^"]*)"')
EXACT_VERSION_RE = re.compile(r"(@|/)v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?/")


def is_pinned(url: str) -> bool:
    """True when the URL contains an exact x.y.z version path segment."""
    return bool(EXACT_VERSION_RE.search(url))


def sri_hash(data: bytes, algo: str = "sha384") -> str:
    digest = hashlib.new(algo, data).digest()
    return f"{algo}-{base64.b64encode(digest).decode()}"


def external_tags(text: str):
    """Yield (match, url, attrs) for third-party script/stylesheet tags."""
    for m in TAG_RE.finditer(text):
        attrs = {a["key"].lower(): a["value"] for a in ATTR_RE.finditer(m["attrs"])}
        name = m["name"].lower()
        if name == "script":
            url = attrs.get("src", "")
        elif attrs.get("rel", "").lower() == "stylesheet":
            url = attrs.get("href", "")
        else:
            continue
        if url.startswith(("http://", "https://", "//")):
            yield m, url, attrs


def check(templates: Path = TEMPLATES) -> list[str]:
    """Return a list of problems; empty means every CDN tag is pinned + hashed."""
    problems = []
    for path in sorted(templates.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        for m, url, attrs in external_tags(text):
            line = text.count("\n", 0, m.start()) + 1
            where = f"{path.relative_to(templates.parent.parent)}:{line}"
            if not is_pinned(url):
                problems.append(f"{where}: not pinned to an exact version: {url}")
            if not attrs.get("integrity", "").startswith(
                ("sha256-", "sha384-", "sha512-")
            ):
                problems.append(f"{where}: missing integrity: {url}")
            if attrs.get("crossorigin") != "anonymous":
                problems.append(f'{where}: missing crossorigin="anonymous": {url}')
    return problems


def fetch(url: str) -> bytes:
    import requests  # only needed for --update/--verify

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


def set_attrs(tag: str, integrity: str) -> str:
    """Return the tag with integrity and crossorigin set (replacing old values)."""
    tag = re.sub(r'\s+integrity="[^"]*"', "", tag)
    tag = re.sub(r'\s+crossorigin(="[^"]*")?', "", tag)
    close = "/>" if tag.endswith("/>") else ">"
    body = tag[: -len(close)].rstrip()
    return f'{body} integrity="{integrity}" crossorigin="anonymous"{close}'


def update(templates: Path = TEMPLATES, fetcher=fetch) -> int:
    cache: dict[str, str] = {}
    failures = 0
    for path in sorted(templates.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        out, pos = [], 0
        for m, url, _ in external_tags(text):
            out.append(text[pos : m.start()])
            tag = m.group(0)
            if not is_pinned(url):
                print(f"skip (not pinned): {url}", file=sys.stderr)
                failures += 1
            else:
                if url not in cache:
                    cache[url] = sri_hash(fetcher(url))
                tag = set_attrs(tag, cache[url])
            out.append(tag)
            pos = m.end()
        out.append(text[pos:])
        new = "".join(out)
        if new != text:
            path.write_text(new, encoding="utf-8")
            print(f"updated {path.name}")
    return failures


def verify(templates: Path = TEMPLATES, fetcher=fetch) -> list[str]:
    problems = []
    for path in sorted(templates.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        for _, url, attrs in external_tags(text):
            stored = attrs.get("integrity", "")
            if not stored:
                continue
            algo = stored.split("-", 1)[0]
            actual = sri_hash(fetcher(url), algo)
            if actual != stored:
                problems.append(f"{path.name}: hash mismatch for {url}: {actual}")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)

    if args.update:
        return 1 if update() else 0
    problems = check() if args.check else verify()
    for p in problems:
        print(p)
    if not problems:
        print(
            "SRI: all third-party tags pinned and hashed"
            if args.check
            else "SRI: all hashes match"
        )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
