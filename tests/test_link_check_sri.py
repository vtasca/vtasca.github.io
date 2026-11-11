"""Tests for scripts/check_links.py and scripts/sri.py.

Run with: python -m unittest discover -s tests -p 'test_link_check_sri.py'
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_links
import sri


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class LinkCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write(self.root, "static/app.css", "body{background:url('img/bg.png')}")
        write(self.root, "static/img/bg.png", "")
        write(
            self.root,
            "blog/index.html",
            '<h1 id="posts">Posts</h1><a href="post.html#intro">p</a>',
        )
        write(
            self.root,
            "blog/post.html",
            '<h2 id="intro">Intro</h2><a href="#intro">self</a>',
        )
        write(
            self.root,
            "index.html",
            '<link rel="stylesheet" href="static/app.css">'
            '<link rel="preconnect" href="https://fonts.example">'
            '<a href="blog/">blog</a><a href="blog/post">pretty url</a>'
            '<a href="https://vtasca.dev/blog/post#intro">abs</a>'
            '<a href="mailto:x@example.com">mail</a>'
            '<a href="https://example.com/x">ext</a>'
            '<img srcset="static/img/bg.png 1x, static/img/bg.png 2x">'
            '<meta property="og:image" content="https://vtasca.dev/static/img/bg.png">',
        )
        write(
            self.root,
            "sitemap.xml",
            "<urlset><url><loc>https://vtasca.dev/blog/post</loc></url></urlset>",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_site_has_no_problems(self):
        report = check_links.check_site(self.root)
        self.assertEqual(report.broken, [])
        self.assertEqual(report.warnings, [])
        self.assertEqual(set(report.external), {"https://example.com/x"})
        self.assertGreater(report.checked, 5)

    def test_missing_file_is_reported(self):
        write(
            self.root,
            "about.html",
            '<a href="missing.html">x</a><img src="static/nope.png">',
        )
        broken = check_links.check_site(self.root).broken
        self.assertEqual(len(broken), 2)
        self.assertTrue(all(b.startswith("about.html:1") for b in broken))

    def test_missing_anchor_is_reported(self):
        write(
            self.root,
            "about.html",
            '<a href="blog/post.html#nope">x</a><a href="#here">y</a>',
        )
        broken = check_links.check_site(self.root).broken
        self.assertEqual(len(broken), 2)
        self.assertIn("no id 'nope'", broken[0])
        self.assertIn("no id 'here'", broken[1])

    def test_link_outside_site_is_reported(self):
        write(self.root, "about.html", '<a href="../../etc/passwd">x</a>')
        self.assertIn("outside the site", check_links.check_site(self.root).broken[0])

    def test_css_and_sitemap_links_are_checked(self):
        write(self.root, "static/app.css", "a{background:url(img/gone.png)}")
        write(
            self.root,
            "sitemap.xml",
            "<urlset><url><loc>https://vtasca.dev/gone</loc></url></urlset>",
        )
        broken = check_links.check_site(self.root).broken
        self.assertEqual(len(broken), 2)

    def test_unrendered_template_is_reported(self):
        write(self.root, "about.html", '<a href="{{ root_prefix }}/x">x</a>')
        self.assertIn(
            "unrendered template", check_links.check_site(self.root).broken[0]
        )

    def test_relative_og_image_is_a_warning(self):
        write(
            self.root,
            "about.html",
            '<meta property="og:image" content="static/img/bg.png">',
        )
        report = check_links.check_site(self.root)
        self.assertEqual(report.broken, [])
        self.assertEqual(len(report.warnings), 1)

    def test_main_exit_codes(self):
        self.assertEqual(check_links.main([str(self.root)]), 0)
        write(self.root, "about.html", '<a href="missing.html">x</a>')
        self.assertEqual(check_links.main([str(self.root)]), 1)
        self.assertEqual(check_links.main([str(self.root / "nope")]), 2)


class SriTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.templates = Path(self.tmp.name) / "src" / "templates"
        self.templates.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_is_pinned(self):
        self.assertTrue(
            sri.is_pinned("https://unpkg.com/gpt-tokenizer@3.0.1/dist/x.js")
        )
        self.assertTrue(
            sri.is_pinned(
                "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/h.js"
            )
        )
        self.assertFalse(sri.is_pinned("https://unpkg.com/highlightjs-copy/dist/x.js"))
        self.assertFalse(sri.is_pinned("https://unpkg.com/pkg@1/dist/x.js"))
        self.assertFalse(sri.is_pinned("https://unpkg.com/pkg@latest/dist/x.js"))

    def test_sri_hash_known_value(self):
        # echo -n "alert('Hello, world.');" | openssl dgst -sha384 -binary | base64 (from the SRI spec)
        self.assertEqual(
            sri.sri_hash(b"alert('Hello, world.');"),
            "sha384-H8BRh8j48O9oYatfu5AZzq6A9RINhZO5H16dQZngK7T62em8MUt1FLm52t+eX6xO",
        )

    def test_update_then_check(self):
        page = self.templates / "page.html"
        page.write_text(
            '<script src="https://unpkg.com/a@1.2.3/a.js"></script>\n'
            '<link rel="stylesheet" href="https://cdn.example/b/2.0.0/b.css" integrity="sha384-old">\n'
            '<link rel="icon" href="https://cdn.example/favicon.ico">\n'
            '<script src="{{static_prefix}}/local.js"></script>\n'
        )
        self.assertEqual(
            len(sri.check(self.templates)), 3
        )  # script: integrity+crossorigin; link: crossorigin
        failures = sri.update(self.templates, fetcher=lambda url: url.encode())
        self.assertEqual(failures, 0)
        text = page.read_text()
        self.assertIn(
            f'integrity="{sri.sri_hash(b"https://unpkg.com/a@1.2.3/a.js")}" crossorigin="anonymous"></script>',
            text,
        )
        self.assertNotIn("sha384-old", text)
        self.assertEqual(text.count("integrity="), 2)
        self.assertEqual(sri.check(self.templates), [])
        self.assertEqual(
            sri.verify(self.templates, fetcher=lambda url: url.encode()), []
        )
        self.assertEqual(
            len(sri.verify(self.templates, fetcher=lambda url: b"changed")), 2
        )

    def test_update_refuses_floating_urls(self):
        page = self.templates / "page.html"
        page.write_text('<script src="https://unpkg.com/a/a.js"></script>')
        self.assertEqual(sri.update(self.templates, fetcher=lambda url: b""), 1)
        self.assertNotIn("integrity", page.read_text())

    def test_repo_templates_pass_check(self):
        self.assertEqual(sri.check(), [])


if __name__ == "__main__":
    unittest.main()
