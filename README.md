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
- Command-W (⌘W) keyboard shortcut to close windows
- Native macOS integration with "Reveal in Finder" support

### Clipboard Integration
- Copy rendered image to clipboard with high-DPI metadata preservation
- Copy diagram source code to clipboard
- Proper device pixel ratio handling for crisp pasted images

## Architecture

- **Platform**: MacOS with high-DPI display support
- **Python**: 3.13 (via uv package manager)
- **Async Runtime**: Async Python with qasync Qt integration
- **GUI Framework**: PySide6 with traditional QWidget (not QML or Qt Quick)
- **File Watching**: Async file watcher (tracks file creation, modification, deletion)
- **Window Management**: Window manager with state persistence (tracks opened files and their windows)
- **Rendering**: Kroki service client (DaC → SVG/PNG)
- **Image Display**: QScrollArea-based viewer with high-DPI scaling
- **Clipboard**: High-DPI image copying with proper metadata preservation

## Usage

```bash
uv run dacwatch --kroki-base=https://kroki.io <dir> [<dir2> ...]
```

### Keyboard Shortcuts

- **Command-W (⌘W)**: Close the active diagram window (Ctrl-W on Windows/Linux)

### Toolbar Actions

- **Toggle SVG/PNG**: Switch between SVG and PNG rendering formats
- **Copy Image**: Copy the current high-DPI rendered image to clipboard
- **Copy Source**: Copy the diagram source code to clipboard  
- **Reveal in Finder**: Open the source file location in Finder (macOS)
