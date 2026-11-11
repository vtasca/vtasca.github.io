"""Tests for build-time dataset stats. Run with: uv run python -m unittest discover tests

Stdlib unittest only (also collected by pytest), and no network: HTTP is faked.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import dataset_stats  # noqa: E402
from dataset_stats import format_date, format_rows, format_size, resolve_stats  # noqa: E402

INFO = {
    "dataset_info": {
        "default": {
            "splits": {"train": {"num_examples": 395400, "num_bytes": 20111184}}
        }
    }
}
HUB = {"lastModified": "2026-11-10T19:19:19.000Z"}


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")

    def json(self):
        return self.payload


def fake_get(url, timeout=None):
    if "datasets-server" in url:
        return FakeResponse(INFO)
    return FakeResponse(HUB)


def failing_get(url, timeout=None):
    raise ConnectionError("no network")


def silent(*args, **kwargs):
    pass


def make_datasets():
    return [
        {
            "id": "wikipedia",
            "huggingface_dataset_name": "wikipedia-pageviews",
            "fallback_rows": "45,892",
            "fallback_size": "15.7 MB",
        }
    ]


class FormattingTests(unittest.TestCase):
    def test_rows(self):
        self.assertEqual(format_rows(395400), "395,400")

    def test_size(self):
        self.assertEqual(format_size(20111184), "19.2 MB")

    def test_date(self):
        self.assertEqual(format_date("2026-11-01T19:19:19.000Z"), "1 Nov 2026")

    def test_bad_date(self):
        self.assertIsNone(format_date("not a date"))
        self.assertIsNone(format_date(None))


class ResolveStatsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache_path = Path(self.tmp.name) / "cache.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_live_fetch_populates_page_and_cache(self):
        datasets = resolve_stats(
            make_datasets(), self.cache_path, offline=False, get=fake_get, log=silent
        )
        d = datasets[0]
        self.assertEqual(d["stats_source"], "live")
        self.assertEqual(d["stats_rows"], "395,400")
        self.assertEqual(d["stats_size"], "19.2 MB")
        self.assertEqual(d["stats_last_updated"], "10 Nov 2026")

        cache = json.loads(self.cache_path.read_text())
        self.assertEqual(cache["wikipedia-pageviews"]["num_rows"], 395400)

    def test_network_failure_uses_cache(self):
        resolve_stats(make_datasets(), self.cache_path, offline=False, get=fake_get, log=silent)
        datasets = resolve_stats(
            make_datasets(), self.cache_path, offline=False, get=failing_get, log=silent
        )
        d = datasets[0]
        self.assertEqual(d["stats_source"], "cache")
        self.assertEqual(d["stats_rows"], "395,400")
        self.assertEqual(d["stats_last_updated"], "10 Nov 2026")

    def test_offline_never_calls_network(self):
        def exploding_get(url, timeout=None):
            raise AssertionError("network used in offline mode")

        datasets = resolve_stats(
            make_datasets(), self.cache_path, offline=True, get=exploding_get, log=silent
        )
        self.assertEqual(datasets[0]["stats_source"], "fallback")

    def test_no_cache_and_no_network_uses_metadata_fallback(self):
        datasets = resolve_stats(
            make_datasets(), self.cache_path, offline=False, get=failing_get, log=silent
        )
        d = datasets[0]
        self.assertEqual(d["stats_source"], "fallback")
        self.assertEqual(d["stats_rows"], "45,892")
        self.assertEqual(d["stats_size"], "15.7 MB")
        self.assertIsNone(d["stats_last_updated"])
        self.assertFalse(self.cache_path.exists())

    def test_unexpected_json_shape_falls_back(self):
        def weird_get(url, timeout=None):
            return FakeResponse({"error": "dataset not found"})

        datasets = resolve_stats(
            make_datasets(), self.cache_path, offline=False, get=weird_get, log=silent
        )
        self.assertEqual(datasets[0]["stats_source"], "fallback")

    def test_http_error_falls_back(self):
        def error_get(url, timeout=None):
            return FakeResponse({}, status=503)

        datasets = resolve_stats(
            make_datasets(), self.cache_path, offline=False, get=error_get, log=silent
        )
        self.assertEqual(datasets[0]["stats_source"], "fallback")

    def test_corrupt_cache_is_ignored(self):
        self.cache_path.write_text("{not json")
        datasets = resolve_stats(
            make_datasets(), self.cache_path, offline=True, get=failing_get, log=silent
        )
        self.assertEqual(datasets[0]["stats_source"], "fallback")

    def test_malformed_cache_entry_is_ignored(self):
        self.cache_path.write_text(json.dumps({"wikipedia-pageviews": {"num_rows": "x"}}))
        datasets = resolve_stats(
            make_datasets(), self.cache_path, offline=True, get=failing_get, log=silent
        )
        self.assertEqual(datasets[0]["stats_source"], "fallback")

    def test_unchanged_data_does_not_rewrite_cache(self):
        resolve_stats(make_datasets(), self.cache_path, offline=False, get=fake_get, log=silent)
        before = self.cache_path.read_text()
        resolve_stats(make_datasets(), self.cache_path, offline=False, get=fake_get, log=silent)
        self.assertEqual(self.cache_path.read_text(), before)

    def test_offline_env_var(self):
        original = dataset_stats.os.environ.get("DATASET_STATS_OFFLINE")
        dataset_stats.os.environ["DATASET_STATS_OFFLINE"] = "1"
        try:
            datasets = resolve_stats(
                make_datasets(), self.cache_path, get=failing_get, log=silent
            )
        finally:
            if original is None:
                del dataset_stats.os.environ["DATASET_STATS_OFFLINE"]
            else:
                dataset_stats.os.environ["DATASET_STATS_OFFLINE"] = original
        self.assertEqual(datasets[0]["stats_source"], "fallback")


if __name__ == "__main__":
    unittest.main()
