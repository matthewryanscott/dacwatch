# DaCWatch: A Diagrams-as-Code Watching tool

## Features

### File Watching
- Watch multiple directories for changes
- Watches for GraphViz (`.dot`), PlantUML (`.puml`, `.plantuml`), Mermaid (`.mermaid`)
- If a new one is created or modified, opens a new window for that diagram if not already opened
- If a diagram is modified, re-renders it in same window if already opened
- If a diagram is deleted, closes its window if open

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

### Recommended: Self-hosted Kroki (Docker)

For best privacy and performance, run your own Kroki instance using the included Docker Compose setup:

```bash
# Start the self-hosted Kroki service (runs on localhost:48000)
cd kroki-self-hosted
docker compose up -d

# Run DaCWatch (uses localhost:48000 by default)
uv run dacwatch <dir> [<dir2> ...]
```

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
