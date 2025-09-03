# AGENTS.md - DaCWatch Coding Guidelines

## Build/Test Commands
- **Run application**: `uv run main.py --kroki-base=https://kroki.io <dir>`
- **Run tests**: `uv run pytest`
- **Run single test**: `uv run pytest path/to/test_file.py::test_function`
- **Install dependencies**: `uv add <package>`
- **Sync environment**: `uv sync`
- **Python version**: 3.13 (managed via `.python-version`)

## Code Style Guidelines
- **Language**: Python 3.13+ with async/await patterns
- **Package manager**: uv (fast Python package manager)
- **GUI Framework**: PySide (traditional QWidget, not QML)
- **Architecture**: Async file watcher + window manager + Kroki renderer
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Imports**: Standard library first, third-party next, local imports last
- **Error handling**: Use try/except blocks for external service calls (Kroki API)
- **Type hints**: Use modern Python typing (requires-python = ">=3.13")
- **File watching**: Support .dot, .puml, .plantuml, .mermaid files
- **Rendering**: SVG preferred, PNG fallback via Kroki service

## TDD Development Process
- **Red-Green-Refactor**: Write failing test, implement minimal code, refactor
- **Test First**: Write unit tests before implementing each component
- **Mock External**: Mock Kroki API, file system, but avoid heavy Qt widget mocking
- **Headless Qt Testing**: Use `pytest-qt` with `QT_QPA_PLATFORM=offscreen` for real Qt widgets in tests
- **Manual Validation**: GUI interactions and file watching require manual testing after automated tests pass
- **Documentation**: Update PLAN.md checkboxes and README.md as features are completed

## Development Workflow
**STOP AND WAIT**: After completing each phase from PLAN.md, the agent MUST stop and wait for manual review and commit before proceeding to the next phase. This allows for:
- Code review and quality checks
- Manual testing of implemented features
- Git commits with meaningful messages
- Opportunity to pause or redirect development

## Qt Testing Best Practices

### Headless Qt Testing
- **Use pytest-qt**: Already installed in dev dependencies
- **Automatic headless mode**: conftest.py sets `QT_QPA_PLATFORM=offscreen`
- **Real widgets over mocks**: Use `qtbot.addWidget()` with actual Qt widgets
- **Widget discovery**: Use `findChildren(QPushButton)` instead of mocking widget creation

### Qt Widget Testing Pattern
```python
def test_widget_behavior(self, qtbot):
    # Create real widget
    widget = MyWidget()
    qtbot.addWidget(widget)
    
    # Test real behavior
    buttons = widget.findChildren(QPushButton)
    assert any("Expected Text" in btn.text() for btn in buttons)
```

### Qt Import Patterns
- **Local imports in methods**: Import Qt widgets inside methods to enable proper mocking when needed
- **Example**: `from PySide6.QtWidgets import QLabel` inside `_setup_toolbar()` instead of at module level

## Recent Implementation Notes
- **Format label**: Added to toolbar on right side, updates automatically with image format
- **Toggle functionality**: Uses callback pattern for re-rendering with new format
- **All tests passing**: 46 tests including UI widget tests via headless Qt

## Project Structure
- Minimal structure: main.py entry point, pyproject.toml for dependencies
- Target: MacOS desktop application for diagram-as-code file watching