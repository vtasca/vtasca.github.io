"""Shared fixtures for the site build tests.

Everything here runs offline: the build is fed committed sample markdown from
tests/fixtures/site instead of content fetched from Notion, so no secrets or
network access are needed.
"""

import importlib.util
import os
import runpy
import shutil
from contextlib import contextmanager
from pathlib import Path

import pytest
from lxml import etree, html

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build.py"


@contextmanager
def chdir(path):
    """build.py resolves src/ and published/ against the working directory."""
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


@pytest.fixture(scope="session")
def build():
    """scripts/build.py imported as a module (its main block does not run)."""
    spec = importlib.util.spec_from_file_location("site_build", BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def site_root(tmp_path_factory):
    """A throwaway project tree: real templates + data metadata, fixture posts."""
    root = tmp_path_factory.mktemp("site")
    src = root / "src"
    shutil.copytree(REPO_ROOT / "src" / "templates", src / "templates")
    shutil.copy(REPO_ROOT / "src" / "data_metadata.json", src / "data_metadata.json")
    shutil.copytree(FIXTURES / "site", src, dirs_exist_ok=True)
    return root


@pytest.fixture(scope="session")
def published(site_root):
    """Run the full build exactly as CI does and return the output directory."""
    with chdir(site_root):
        runpy.run_path(str(BUILD_SCRIPT), run_name="__main__")
    return site_root / "published"


@pytest.fixture
def in_repo():
    """Run a test with the repo root as cwd, so build.py finds src/templates."""
    with chdir(REPO_ROOT):
        yield REPO_ROOT


def parse_html(path):
    return html.fromstring(Path(path).read_bytes())


def parse_xml(path):
    return etree.fromstring(Path(path).read_bytes())
