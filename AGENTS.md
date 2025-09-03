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
- **Mock External**: Mock Kroki API, file system, GUI components in tests
- **Manual Validation**: GUI interactions and file watching require manual testing after automated tests pass
- **Documentation**: Update PLAN.md checkboxes and README.md as features are completed

## Development Workflow
**STOP AND WAIT**: After completing each phase from PLAN.md, the agent MUST stop and wait for manual review and commit before proceeding to the next phase. This allows for:
- Code review and quality checks
- Manual testing of implemented features
- Git commits with meaningful messages
- Opportunity to pause or redirect development

## Project Structure
- Minimal structure: main.py entry point, pyproject.toml for dependencies
- Target: MacOS desktop application for diagram-as-code file watching