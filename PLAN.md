# DaCWatch Implementation Plan

## Documentation Updates
**IMPORTANT**: When completing any task below, update the corresponding checkboxes in this PLAN.md and update README.md if new features/usage patterns are added.

## Phase 1: Core Infrastructure (TDD)
- [ ] **CLI Argument Parser**: Write tests for Typer CLI argument parsing, then implement
- [ ] **Configuration**: Test config object creation/validation, then implement
- [ ] **File Type Detection**: Test file extension mapping, then implement logic
- [ ] **Basic Application Structure**: Test async event loop setup, then implement
- [ ] **Manual Validation**: Run `uv run main.py --help` to verify CLI works

## Phase 2: File Watching System (TDD)
- [ ] **Async File Watcher**: Test directory monitoring with mock filesystem, then implement
- [ ] **Event Handling**: Test event detection with temporary files, then implement
- [ ] **File Filter**: Test file type filtering logic, then implement
- [ ] **Event Queue**: Test event buffering/debouncing, then implement
- [ ] **Manual Validation**: Create/modify/delete test files to verify watching works

## Phase 3: Window Management (TDD)
- [ ] **Window Registry**: Test file-to-window mapping, then implement
- [ ] **Window Factory**: Test window creation logic (mock QMainWindow), then implement
- [ ] **Window Cleanup**: Test window cleanup on file deletion, then implement
- [ ] **Window State**: Test state persistence, then implement
- [ ] **Manual Validation**: Open/close windows manually to verify behavior

## Phase 4: Kroki Integration (TDD)
- [ ] **HTTP Client**: Test HTTP requests with mock aiohttp responses, then implement
- [ ] **Diagram Type Detection**: Test extension-to-type mapping, then implement
- [ ] **Request Builder**: Test API request formatting, then implement
- [ ] **Response Handler**: Test SVG/PNG response parsing, then implement
- [ ] **Error Handling**: Test network/API error scenarios, then implement
- [ ] **Manual Validation**: Test with real Kroki service using sample diagrams

## Phase 5: PySide GUI Components (Limited TDD)
- [ ] **Main Application**: Test QApplication initialization logic, then implement
- [ ] **Diagram Window**: Test window creation/setup (mock Qt), then implement
- [ ] **Image Display**: Test image loading logic, then implement
- [ ] **Toolbar/Menu**: Test button creation/signals, then implement
- [ ] **Auto-scaling**: Test scaling calculations, then implement
- [ ] **Manual Validation**: Visual testing of GUI components and interactions

## Phase 6: User Interactions (Limited TDD)
- [ ] **Format Toggle**: Test format switching logic, then implement
- [ ] **Copy Image**: Test clipboard operations (mock), then implement
- [ ] **Copy Source**: Test source code copying, then implement
- [ ] **Reveal in Finder**: Test subprocess calls, then implement
- [ ] **Window Controls**: Test event handling, then implement
- [ ] **Manual Validation**: Interactive testing of all user actions

## Phase 7: Advanced Features (TDD)
- [ ] **Auto-refresh**: Test file change detection and re-rendering, then implement
- [ ] **Error Display**: Test error message handling, then implement
- [ ] **Preferences**: Test settings persistence, then implement
- [ ] **Multiple Kroki Services**: Test endpoint switching, then implement
- [ ] **File Validation**: Test syntax checking, then implement
- [ ] **Manual Validation**: End-to-end testing of advanced workflows

## Phase 8: Testing & Polish
- [ ] **Unit Tests**: Test file watcher, Kroki client, window management
- [ ] **Integration Tests**: End-to-end workflow testing
- [ ] **Error Scenarios**: Test network failures, malformed files, service downtime
- [ ] **Performance**: Optimize for large directories, many open windows
- [ ] **Memory Management**: Clean up resources, prevent leaks

## Core Components Architecture

### FileWatcher
```python
class FileWatcher:
    async def watch_directories(self, paths: list[str])
    async def handle_file_event(self, event: FileEvent)
```

### WindowManager
```python
class WindowManager:
    def get_window_for_file(self, filepath: str) -> DiagramWindow | None
    def create_window(self, filepath: str) -> DiagramWindow
    def close_window(self, filepath: str)
```

### KrokiClient
```python
class KrokiClient:
    async def render_diagram(self, source: str, diagram_type: str, format: str) -> bytes
    def get_diagram_type(self, filepath: str) -> str
```

### DiagramWindow
```python
class DiagramWindow(QMainWindow):
    def display_image(self, image_data: bytes, format: str)
    def toggle_format(self)
    def copy_image_to_clipboard(self)
    def copy_source_to_clipboard(self)
    def reveal_in_finder(self)
```

## File Extensions → Diagram Types
- `.dot` → `graphviz`
- `.puml`, `.plantuml` → `plantuml` 
- `.mermaid` → `mermaid`

## Dependencies
- `pyside6` - GUI framework
- `aiohttp` - Async HTTP client for Kroki
- `watchdog` - File system monitoring
- `typer` - CLI framework with rich help
- `pytest` - Testing framework