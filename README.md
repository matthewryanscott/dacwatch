# DaCWatch: A Diagrams-as-Code Watching tool

## Features

- Watch multiple directories for changes
- Watches for GraphViz (`.dot`), PlantUML (`.puml`, `.plantuml`), Mermaid (`.mermaid`)
- If a new one is created or modified, opens a new window for that diagram if not already opened
- If a diagram is modified, re-renders it in same window if already opened
- If a diagram is deleted, closes its window if open
- Uses a Kroki service to render diagrams as SVG or PNG
- Defaults to SVG, allows switching to PNG in each window
- Button to copy rendered image to clipboard
- Button to copy DaC source to clipboard
- Button reveal file in finder

## Architecture

- MacOS
- Python 3.13 (via uv)
- Async Python
- PySide for PyQt interface
- Traditional QWidget (not QML or Qt Quick)
- Async file watcher (tracks file creation, modification, deletion)
- Window manager (tracks opened files and their windows)
- Kroki renderer (DaC -> SVG/PNG)
- SVG renderer (scaled to fit window size)
- PNG renderer (scaled to fit window size)

## Usage

```bash
uv run dacwatch --kroki-base=https://kroki.io <dir> [<dir2> ...]
```
