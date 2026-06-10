# DaCWatch: Live preview for diagrams-as-code

DaCWatch watches diagram files, renders them through Kroki, and opens a desktop preview window for each diagram you create or change.

## Who this is for

DaCWatch is aimed at developers who:
- already keep diagrams in source files
- are comfortable launching a desktop app from the command line
- want a lightweight local preview loop instead of living in a browser tab
- use Graphviz, PlantUML, Mermaid, or Markdown docs with diagram fences

This project is especially useful if you already edit diagrams in your normal editor and want the preview window to stay out of the way until something changes.

## What makes it useful

- **Fast feedback loop**: save a diagram file and the preview refreshes automatically
- **Desktop-native viewing**: separate windows, keyboard shortcuts, zooming, and clipboard support
- **Works with docs repos**: Markdown fenced diagrams are supported alongside standalone diagram files
- **Local-first option**: point it at a self-hosted Kroki stack for privacy and speed

## Alpha status

DaCWatch is an **alpha-quality developer tool**.

That means:
- the core workflow is already usable
- the codebase has automated tests and is actively being polished
- some ergonomics and persistence features are still incomplete
- macOS is the primary target; Linux and Windows paths exist but need more real-world validation

If that tradeoff sounds acceptable, DaCWatch is ready for experimentation.

## Quick start

### Requirements
- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Optional: Docker, if you want a private local Kroki service

### Install
```bash
uv sync
```

### Optional: Install the CLI globally for local development
If you want to invoke `dacwatch` from any directory without prefixing it with `uv run`, install this repo as an editable global tool:

```bash
uv tool install -e .
```

Then you can run:

```bash
dacwatch .
dacwatch docs diagrams
```

To pick up local changes later, reinstall or upgrade the tool:

```bash
uv tool upgrade dacwatch
```

To remove it:

```bash
uv tool uninstall dacwatch
```

This is especially convenient if you want DaCWatch available everywhere while still developing it from this checkout.

### Optional: Build the macOS app (icon + menu-bar name)

DaCWatch runs as a single instance: the first `dacwatch <path>` launches the app, and later
invocations hand their paths to that running instance over a local socket. On macOS, building
the `.app` bundle gives the running app its proper Dock icon and the "DaCWatch" menu-bar name,
and lets it come to the foreground when a diagram opens:

```bash
./scripts/build_app.sh
```

This produces `dist/DaCWatch.app` from `resources/icon.png` (the bundle stays out of version
control). The bundle runs the project's `.venv`, so keep `uv sync` up to date. Once built,
`dacwatch <path>` launches via the bundle automatically; without it, DaCWatch falls back to a
detached background process (same behavior, generic icon and name).

### 30-second first run

```bash
# 1) Start the bundled local Kroki stack
cd kroki-self-hosted
docker compose up -d
cd ..

# 2) Watch the current directory
uv run dacwatch .

# or, if you installed the CLI globally
# dacwatch .
```

### Run with self-hosted Kroki
```bash
cd kroki-self-hosted
docker compose up -d
cd ..
uv run dacwatch <dir> [<dir2> ...]
```

DaCWatch validates the Kroki connection at startup. If the local service is not running yet, start it with the Docker Compose command above and try again.

### Run with public Kroki
```bash
uv run dacwatch --kroki-base=https://kroki.io <dir> [<dir2> ...]
```

## Features

### Supported files

| Source | Detected as | Notes |
| --- | --- | --- |
| `.dot` | Graphviz | Rendered through Kroki |
| `.puml`, `.plantuml` | PlantUML | Rendered through Kroki |
| `.mermaid` | Mermaid | Defaults to PNG for best Qt compatibility |
| `.md` fenced blocks | PlantUML, Mermaid, Graphviz | Watches supported code fences like ` ```plantuml `, ` ```mermaid `, and ` ```dot ` |

### File Watching
- Watch multiple directories for changes
- Watches Graphviz (`.dot`), PlantUML (`.puml`, `.plantuml`), Mermaid (`.mermaid`), and Markdown files with supported diagram fences
- Opens a new preview window when a new diagram appears
- Re-renders an existing preview window when a watched diagram changes
- Closes the preview window when the source diagram is deleted

### What happens when a file changes
1. Create or edit a supported diagram file in any watched directory.
2. DaCWatch detects the change and sends diagram source to Kroki.
3. DaCWatch opens a new preview window or refreshes the existing one.
4. Delete the source file and DaCWatch closes that preview window.

### Diagram Rendering
- Uses a Kroki service to render diagrams as SVG or PNG
- Defaults to SVG for Graphviz and PlantUML, and PNG for Mermaid for best Qt compatibility
- Lets each preview window switch formats independently
- High-DPI display support with 2x rendering on Retina displays
- Zoomable graphics view with automatic scrollbars
- Clean white background for better diagram visibility
- Shows render errors inline and allows copying full Kroki error output

### User Interface
- Toolbar with format toggle, copy, and file management buttons
- Format indicator showing current SVG/PNG mode
- Cross-platform keyboard shortcuts (Cmd on macOS, Ctrl on Linux/Windows)
- Native file manager integration with "Reveal" support

### Clipboard Integration
- Copy rendered image to clipboard with high-DPI metadata preservation
- Copy diagram source code to clipboard
- Proper device pixel ratio handling for crisp pasted images
- Paste diagram source from the clipboard (`Cmd/Ctrl+V`) to render it in a new window — no file needed. The diagram type is auto-detected by trying the source against the supported Kroki types (Mermaid, PlantUML, Graphviz) until one renders.

## Architecture

- **Platform**: Desktop app designed for macOS first, with Linux and Windows support in code paths
- **Python**: 3.13 (via uv package manager)
- **Async Runtime**: Async Python with qasync Qt integration
- **GUI Framework**: PySide6 with traditional QWidget (not QML or Qt Quick)
- **File Watching**: Async file watcher (tracks file creation, modification, deletion)
- **Window Management**: Window manager with state persistence (tracks opened files and their windows)
- **Rendering**: Kroki service client (DaC → SVG/PNG)
- **Image Display**: QGraphicsView-based viewer with high-DPI scaling
- **Clipboard**: High-DPI image copying with proper metadata preservation

## Usage

### Common commands

```bash
# Watch one directory
uv run dacwatch diagrams

# Watch several directories at once
uv run dacwatch diagrams docs examples

# Validate configuration without launching UI
uv run dacwatch --dry-run diagrams

# Show informational logs
uv run dacwatch --verbose diagrams

# Show detailed watcher/render debug logs
uv run dacwatch --debug diagrams
```

### CLI options

| Option | Description | Default |
| --- | --- | --- |
| `DIRECTORIES...` | One or more directories to watch | Required |
| `--kroki-base TEXT` | Kroki service base URL | `http://localhost:48000` |
| `--dry-run / --no-dry-run` | Validate config and exit without starting UI | `--no-dry-run` |
| `--verbose` | Show informational startup and lifecycle logs | `off` |
| `--debug` | Show detailed debugging logs, including file watcher events | `off` |

Run `uv run dacwatch --help` for full Typer-generated help.

### Recommended: Self-hosted Kroki (Docker)

For best privacy, startup speed, and local-only rendering, run your own Kroki instance using the included Docker Compose setup:

```bash
# Start the self-hosted Kroki service (runs on localhost:48000)
cd kroki-self-hosted
docker compose up -d

# Run DaCWatch (uses localhost:48000 by default)
uv run dacwatch <dir> [<dir2> ...]
```

See [`kroki-self-hosted/README.md`](kroki-self-hosted/README.md) for more detail about local Kroki and Niolesk services.

### Alternative: Public Kroki Service

⚠️ **Privacy Warning**: Using the public Kroki service sends your diagram source code to a third-party server.

If you prefer not to run Docker, you can use the public Kroki endpoint:

```bash
uv run dacwatch --kroki-base=https://kroki.io <dir> [<dir2> ...]
```

### Keyboard shortcuts

DaCWatch uses `Cmd` on macOS and `Ctrl` on Linux and Windows for standard shortcuts.

| Area | Shortcut | Action |
| --- | --- | --- |
| Window management | `Cmd/Ctrl+W` | Close active preview window |
| Window management | `Cmd/Ctrl+Shift+]` | Cycle to next preview window |
| Window management | `Cmd/Ctrl+Shift+[` | Cycle to previous preview window |
| Window management | `Cmd/Ctrl+T` | Toggle always-on-top on macOS |
| Window management | `Cmd/Ctrl+R` | Reveal source file in file manager |
| Viewing | `Cmd/Ctrl++` or `Cmd/Ctrl+=` | Zoom in |
| Viewing | `Cmd/Ctrl+-` | Zoom out |
| Viewing | `Cmd/Ctrl+0` | Reset zoom to 100% |
| Viewing | `F` | Fit window to diagram |
| Viewing | `S` | Toggle auto-scale |
| Viewing | Double-click | Fit window to diagram |
| Viewing | Pinch gesture | Zoom in or out on trackpad |
| Clipboard | `Cmd/Ctrl+C` | Copy rendered image with white background |
| Clipboard | `Cmd/Ctrl+Alt+C` | Copy rendered image with transparency |
| Clipboard | `Cmd/Ctrl+Shift+C` | Copy diagram source |
| Clipboard | `Cmd/Ctrl+V` | Paste clipboard source as a new diagram (auto-detects type) |
| Format | `Cmd/Ctrl+F` | Toggle SVG and PNG |

### Toolbar actions

| Control | Action |
| --- | --- |
| `SVG` / `PNG` | Switch render format for current window |
| `📋 Image` | Copy current render with white background |
| `📋 Transparent` | Copy current render with transparency |
| `Source` | Copy diagram source text |
| `Error` | Copy full Kroki error response when render fails |
| `Fit` | Resize window to fit current diagram |
| `Reveal` | Open source file location in platform file manager |

## Known rough edges

- DaCWatch depends on a reachable Kroki endpoint; if Kroki is down, the app cannot render
- Preferences are still limited, and not every user-facing setting persists yet
- Non-macOS code paths exist, but they need more manual validation in real developer environments
- Documentation visuals are still catching up to the current app behavior

## Platform support

- **Actively developed on**: macOS
- **Designed to support**: Linux and Windows through Qt, Typer, and Kroki-based code paths
- **Behavior to verify manually on non-macOS systems**: file manager reveal integration, window focus behavior, and clipboard details

## Development

### Run tests
```bash
uv run pytest
```

### Headless Qt test mode
Tests use `pytest-qt` with `QT_QPA_PLATFORM=offscreen`, so widget behavior can be exercised without opening real windows.

### Current automated coverage
- 177 collected tests across CLI, file watching, rendering, window management, clipboard, markdown parsing, and zoom behavior
- `uv run dacwatch --help` provides the generated CLI reference

## Project status

DaCWatch is already usable for day-to-day diagram previewing, but project still in active polish phase.

### Roadmap highlights
- Improve in-window error display polish
- Add user preferences and persisted settings
- Support switching between multiple Kroki services
- Add diagram validation before render
- Expand integration, failure-mode, performance, and memory tests

## Current limitations

- DaCWatch requires a reachable Kroki endpoint to render anything
- Syntax validation happens at render time, not before you edit or save
- Preferences are not persisted yet
- Multi-endpoint Kroki switching is not implemented yet
- Screenshot-quality docs visuals are illustrative; final polished app capture workflow still needs manual curation

## Troubleshooting

| Problem | What to check |
| --- | --- |
| App exits at startup with a Kroki error | Start the bundled local stack with `cd kroki-self-hosted && docker compose up -d`, or rerun with `--kroki-base=https://kroki.io` |
| No preview window appears | Confirm file extension or Markdown fence language is supported and file lives under watched directory |
| Error window appears after startup | Check Kroki endpoint availability and copy error output from toolbar for exact response |
| Public Kroki feels slow | Switch to local Docker-backed Kroki on `http://localhost:48000` |
| Reveal action behaves differently by OS | Verify local file manager integration on your platform |
| Clipboard output looks blurry | Use PNG or white-background copy mode and test target app's paste behavior |

## License

MIT. See [LICENSE](LICENSE).
