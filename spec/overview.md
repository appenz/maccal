# macCal library

A python library to access macOS calendars via PyObjC and EventKit. Compatible with macOS 26 Tahoe.

The library includes functions to:
- List available calendars
- Find calendar events based on keywords (with field-specific or whole-record search)
- Read calendar events in a date range (recurring events auto-expanded)
- Add, edit and delete calendar events (with recurring event span control)
- Find available free time slots

The library has a comprehensive set of tests, they can be invoked via 'make test'. Packages are managed with uv.

# Directory Layout

- `src/maccal/` - Library source code
- `tests/` - Pytest test suite (pure-Python and macOS integration tests)
- `benchmarks/` - Performance benchmarks for query and search operations
- `examples/` - Runnable example scripts
- `spec/` - Project specification

# Packaging

- Build system: `uv_build` (configured in pyproject.toml)
- `uv build` produces sdist + wheel in `dist/`
- `uv publish` uploads to PyPI (requires `UV_PUBLISH_TOKEN` or `~/.pypirc`)
- `uv publish --index-url https://test.pypi.org/simple/` for Test PyPI
- Makefile targets: `make build` (build), `make clean` (remove artifacts)
- Classifiers: macOS, Python 3.13, Apache 2.0, Scheduling
