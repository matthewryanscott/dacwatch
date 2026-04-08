# DaCWatch: Live preview for diagrams-as-code

DaCWatch watches diagram files, renders them through Kroki, and opens a desktop preview window for each diagram you create or change.

## Quick start

### Requirements
- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Optional: Docker, if you want a private local Kroki service

### Install
```bash
uv sync
```

### Run with self-hosted Kroki
```bash
cd kroki-self-hosted
docker compose up -d
cd ..
uv run dacwatch <dir> [<dir2> ...]
```

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
- Defaults to SVG, allows switching to PNG in each window
- High-DPI display support with 2x rendering on Retina displays
- QScrollArea-based image display with automatic scrollbars
- Clean white background for better diagram visibility

### User Interface
- Toolbar with format toggle, copy, and file management buttons
- Format indicator showing current SVG/PNG mode
- Cross-platform keyboard shortcuts (Cmd on macOS, Ctrl on Linux/Windows)
- Native file manager integration with "Reveal" support

### Clipboard Integration
- Copy rendered image to clipboard with high-DPI metadata preservation
- Copy diagram source code to clipboard
- Proper device pixel ratio handling for crisp pasted images

## Architecture

- **Platform**: Cross-platform (macOS, Linux, Windows) with high-DPI display support
- **Python**: 3.13 (via uv package manager)
- **Async Runtime**: Async Python with qasync Qt integration
- **GUI Framework**: PySide6 with traditional QWidget (not QML or Qt Quick)
- **File Watching**: Async file watcher (tracks file creation, modification, deletion)
- **Window Management**: Window manager with state persistence (tracks opened files and their windows)
- **Rendering**: Kroki service client (DaC → SVG/PNG)
- **Image Display**: QScrollArea-based viewer with high-DPI scaling
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
```

### CLI options

| Option | Description | Default |
| --- | --- | --- |
| `DIRECTORIES...` | One or more directories to watch | Required |
| `--kroki-base TEXT` | Kroki service base URL | `http://localhost:48000` |
| `--dry-run / --no-dry-run` | Validate config and exit without starting UI | `--no-dry-run` |

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

### Keyboard Shortcuts

#### Window Management
- **Cmd-W / Ctrl-W**: Close the active diagram window
- **Cmd-Shift-] / Ctrl-Shift-]**: Cycle to next window
- **Cmd-Shift-[ / Ctrl-Shift-[**: Cycle to previous window
- **Cmd-T / Ctrl-T**: Toggle always-on-top mode
- **Cmd-R / Ctrl-R**: Reveal file in file manager

#### Viewing & Navigation
- **Cmd-+ / Ctrl-+**: Zoom in
- **Cmd-- / Ctrl--**: Zoom out
- **Cmd-0 / Ctrl-0**: Reset zoom to 100%
- **F**: Fit window to diagram size
- **Double-click**: Fit window to diagram size
- **Pinch gesture**: Zoom in/out (trackpad)

#### Clipboard Operations
- **Cmd-C / Ctrl-C**: Copy rendered image to clipboard
- **Cmd-Option-C / Ctrl-Alt-C**: Copy image with white background
- **Cmd-Shift-C / Ctrl-Shift-C**: Copy diagram source code

#### Format Control
- **Cmd-F / Ctrl-F**: Toggle between SVG and PNG rendering

### Toolbar Actions

- **Toggle SVG/PNG**: Switch between SVG and PNG rendering formats
- **Copy Image**: Copy the current high-DPI rendered image to clipboard
- **Copy Source**: Copy the diagram source code to clipboard
- **Reveal**: Open the source file location in file manager
