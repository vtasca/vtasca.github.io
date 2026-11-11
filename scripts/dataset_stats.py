"""Build-time Hugging Face stats for the data page.

At build time we ask two public, unauthenticated Hugging Face endpoints for
each dataset's row count, size and last-modified date. Results are written to
a JSON cache that is committed to the repo, so a build without network (or
with Hugging Face down) still renders the last known numbers instead of
"Loading..." or a stale hand-written guess.

Set DATASET_STATS_OFFLINE=1 to skip the network entirely and use the cache.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

INFO_URL = "https://datasets-server.huggingface.co/info?dataset={repo}"
HUB_URL = "https://huggingface.co/api/datasets/{repo}"
HF_OWNER = "vtasca"
TIMEOUT_SECONDS = 10


def format_rows(num_rows):
    return f"{num_rows:,}"


def format_size(num_bytes):
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def format_date(iso_timestamp):
    """'2026-10-29T14:53:35.000Z' -> '29 Oct 2026'. Returns None if unparseable."""
    if not iso_timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return f"{parsed.day} {parsed.strftime('%b %Y')}"


def fetch_stats(dataset_name, get=requests.get):
    """Fetch raw stats for one dataset. Raises on any network or shape error."""
    repo = f"{HF_OWNER}/{dataset_name}"

    info = get(INFO_URL.format(repo=repo), timeout=TIMEOUT_SECONDS)
    info.raise_for_status()
    split = info.json()["dataset_info"]["default"]["splits"]["train"]

    hub = get(HUB_URL.format(repo=repo), timeout=TIMEOUT_SECONDS)
    hub.raise_for_status()
    last_modified = hub.json().get("lastModified")

    return {
        "num_rows": int(split["num_examples"]),
        "num_bytes": int(split["num_bytes"]),
        "last_modified": last_modified,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _without_fetched_at(stats):
    """Compare stats ignoring fetch time, so unchanged data doesn't rewrite the cache."""
    if not isinstance(stats, dict):
        return stats
    return {k: v for k, v in stats.items() if k != "fetched_at"}


def _is_valid(stats):
    return (
        isinstance(stats, dict)
        and isinstance(stats.get("num_rows"), int)
        and isinstance(stats.get("num_bytes"), int)
    )


def load_cache(cache_path):
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(cache_path, cache):
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, sort_keys=True)
        f.write("\n")


def resolve_stats(datasets, cache_path, offline=None, get=requests.get, log=print):
    """Attach display-ready stats to each dataset dict, in place.

    Order of preference per dataset: live fetch -> cache -> fallback_* fields
    from data_metadata.json. Successful fetches update the cache file.
    """
    if offline is None:
        offline = os.environ.get("DATASET_STATS_OFFLINE") == "1"

    cache = load_cache(cache_path)
    cache_changed = False

    for dataset in datasets:
        name = dataset.get("huggingface_dataset_name")
        stats = None
        source = "fallback"

        if name and not offline:
            try:
                stats = fetch_stats(name, get=get)
                source = "live"
                if _without_fetched_at(cache.get(name)) != _without_fetched_at(stats):
                    cache[name] = stats
                    cache_changed = True
            except Exception as e:  # network, HTTP, or unexpected JSON shape
                log(f"dataset_stats: live fetch failed for {name}: {e}")

        if stats is None and _is_valid(cache.get(name)):
            stats = cache[name]
            source = "cache"

        if stats is not None:
            dataset["stats_rows"] = format_rows(stats["num_rows"])
            dataset["stats_size"] = format_size(stats["num_bytes"])
            dataset["stats_last_updated"] = format_date(stats.get("last_modified"))
        else:
            dataset["stats_rows"] = dataset.get("fallback_rows", "—")
            dataset["stats_size"] = dataset.get("fallback_size", "—")
            dataset["stats_last_updated"] = None
        dataset["stats_source"] = source
        log(f"dataset_stats: {name or dataset.get('id')}: using {source} stats")

    if cache_changed:
        try:
            save_cache(cache_path, cache)
        except OSError as e:
            log(f"dataset_stats: could not write cache {cache_path}: {e}")

    return datasets
