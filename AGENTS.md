## Cursor Cloud specific instructions

This is a Python-based static site generator for [vtasca.dev](https://vtasca.dev). It uses `uv` as the package manager with Python 3.13.

### Key commands

- **Install deps:** `uv sync`
- **Build site:** `uv run python scripts/build.py` — generates static HTML into `published/`
- **Dev server:** `uv run python scripts/serve.py` — serves on `http://localhost:8000` with auto-rebuild on `src/` changes
- **Fetch blog content from Notion:** `uv run python scripts/fetch.py` — requires `NOTION_TOKEN` and `NOTION_DATABASE_ID` env vars (optional; repo ships with pre-fetched content)

### Notes

- No linter, formatter, or test suite is configured. The build script (`scripts/build.py`) succeeding is the primary correctness check.
- The Notion fetch step is optional for local development; the repo includes pre-fetched blog markdown and metadata in `src/blog/md/` and `src/blog_metadata.json`.
- `uv` must be on PATH. It is installed to `$HOME/.local/bin` via the official installer.
- Python 3.13 is required (specified in `.python-version`); install via `uv python install 3.13` if not available.
