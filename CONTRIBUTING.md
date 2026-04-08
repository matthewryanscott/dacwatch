# Contributing to DaCWatch

Thanks for your interest in improving DaCWatch.

DaCWatch is currently an **alpha-quality developer tool** focused primarily on macOS. Contributions are welcome, especially around reliability, developer workflow, GUI polish, and cross-platform validation.

## Before you start

- Read the main project overview in [README.md](README.md)
- Check for existing issues before starting a larger change
- Prefer small, focused pull requests over large mixed changes
- If your change affects user-facing behavior, update `README.md` and `PLAN.md` as appropriate

## Local setup

### Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Optional: Docker, if you want to run the bundled local Kroki stack

### Install dependencies

```bash
uv sync --group dev
```

### Run the app

Using the bundled self-hosted Kroki stack:

```bash
cd kroki-self-hosted
docker compose up -d
cd ..
uv run dacwatch .
```

Or use the public service:

```bash
uv run dacwatch --kroki-base=https://kroki.io .
```

### Optional global editable install

If you want the CLI available from anywhere while developing:

```bash
uv tool install -e .
```

Then invoke it directly:

```bash
dacwatch .
```

## Running tests

Run the full automated test suite with:

```bash
uv run pytest
```

The test suite uses `pytest-qt` with headless Qt (`QT_QPA_PLATFORM=offscreen`) so widget behavior can be exercised without opening real windows.

## Manual validation for GUI changes

Automated tests are helpful, but GUI changes still need manual validation.

When you touch UI, window management, clipboard behavior, file watching, or platform-specific integration, test these manually where relevant:

- open a watched directory and confirm preview windows appear
- modify a supported file and confirm the preview refreshes
- delete a watched file and confirm the preview window closes
- toggle SVG/PNG and verify the render updates
- test zoom, fit, auto-scale, and keyboard shortcuts
- test copy image, copy transparent image, and copy source
- test Kroki failure scenarios if your change affects rendering or startup
- test macOS-specific behaviors like reveal integration and always-on-top if applicable

If your change affects Linux or Windows code paths, note what you verified and what remains untested.

## Code and test expectations

- Python 3.13+
- Prefer clear, typed, maintainable code over clever abstractions
- Keep changes scoped to a single concern when possible
- Add or update tests for non-trivial behavior changes
- Mock external services where practical, but prefer real Qt widgets over heavy widget mocking

Useful commands:

```bash
# Run all tests
uv run pytest

# Run one test module
uv run pytest tests/test_kroki_client.py

# Run one test
uv run pytest tests/test_cli.py::test_cli_help

# Verify the CLI surface
uv run dacwatch --help

# Build packages
uv build
```

## Documentation expectations

Please update documentation when your change affects:

- installation or usage
- supported file types or workflows
- keyboard shortcuts or UI controls
- troubleshooting steps
- development workflow

At minimum, update `README.md` for user-facing changes.

## Pull requests

A good pull request should include:

- a short explanation of the problem
- a summary of the change
- notes about tests run
- notes about any manual GUI validation performed
- screenshots or short recordings for visible UI changes, if practical

## Issue reports

If you are filing an issue instead of sending a PR, helpful reports include:

- macOS / Linux / Windows version
- Python version
- how DaCWatch was launched (`uv run`, `uv tool`, etc.)
- Kroki endpoint used (local or public)
- sample diagram input if the problem is renderer-specific
- logs or exact error text

Thanks for helping make DaCWatch more useful.
