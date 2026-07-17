import stat

import pytest

from dacwatch import petrinet
from dacwatch.petrinet import (
    PetrinetTransformError,
    is_petrinet_supported,
    petrinet_to_dot,
    velocitron_viz_path,
)


@pytest.fixture(autouse=True)
def clear_viz_cache():
    """Reset the cached CLI lookup around every test."""
    velocitron_viz_path.cache_clear()
    yield
    velocitron_viz_path.cache_clear()


def _fake_viz(tmp_path, script_body):
    """Create a fake velocitron-viz executable script."""
    script = tmp_path / "velocitron-viz"
    script.write_text("#!/bin/sh\n" + script_body)
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_supported_when_cli_on_path(monkeypatch):
    """Petrinet support is enabled when velocitron-viz is on PATH."""
    monkeypatch.setattr(
        petrinet.shutil, "which", lambda name: "/usr/local/bin/velocitron-viz"
    )
    assert is_petrinet_supported() is True


def test_not_supported_when_cli_missing(monkeypatch):
    """Petrinet support is disabled when velocitron-viz is absent."""
    monkeypatch.setattr(petrinet.shutil, "which", lambda name: None)
    assert is_petrinet_supported() is False


def test_cli_lookup_is_cached(monkeypatch):
    """The PATH lookup happens once (startup check), then is cached."""
    calls = []

    def fake_which(name):
        calls.append(name)
        return "/usr/local/bin/velocitron-viz"

    monkeypatch.setattr(petrinet.shutil, "which", fake_which)
    is_petrinet_supported()
    is_petrinet_supported()
    assert calls == ["velocitron-viz"]


@pytest.mark.asyncio
async def test_petrinet_to_dot_success(tmp_path, monkeypatch):
    """A successful transform returns the CLI's stdout as DOT source."""
    script = _fake_viz(tmp_path, 'echo "digraph net { p1 -> t1 }"\n')
    monkeypatch.setattr(petrinet, "velocitron_viz_path", lambda: str(script))

    dot = await petrinet_to_dot("example.petrinet")

    assert "digraph net { p1 -> t1 }" in dot


@pytest.mark.asyncio
async def test_petrinet_to_dot_passes_flags_and_file_path(tmp_path, monkeypatch):
    """The CLI gets --plain-labels (Kroki-compatible DOT) and the file path."""
    script = _fake_viz(tmp_path, 'echo "$@"\n')
    monkeypatch.setattr(petrinet, "velocitron_viz_path", lambda: str(script))

    dot = await petrinet_to_dot("/some/net.petrinet")

    assert dot.strip() == "--plain-labels /some/net.petrinet"


@pytest.mark.asyncio
async def test_petrinet_to_dot_failure(tmp_path, monkeypatch):
    """A nonzero exit raises PetrinetTransformError with stderr as detail."""
    script = _fake_viz(tmp_path, 'echo "parse error: bad arc" >&2\nexit 2\n')
    monkeypatch.setattr(petrinet, "velocitron_viz_path", lambda: str(script))

    with pytest.raises(PetrinetTransformError) as exc_info:
        await petrinet_to_dot("bad.petrinet")

    assert "status 2" in str(exc_info.value)
    assert "parse error: bad arc" in exc_info.value.detail


@pytest.mark.asyncio
async def test_petrinet_to_dot_missing_cli(monkeypatch):
    """Transforming without the CLI installed raises PetrinetTransformError."""
    monkeypatch.setattr(petrinet, "velocitron_viz_path", lambda: None)

    with pytest.raises(PetrinetTransformError, match="not installed"):
        await petrinet_to_dot("net.petrinet")
