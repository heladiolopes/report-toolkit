# Repository guide

## Project structure

- Source code lives in `src/report_toolkit/`.
- Tests live in `tests/`.
- Keep the top-level package structure shallow and easy to navigate.
- The main architectural areas are:
  - `composer` — public composition API and document construction.
  - `model` — internal document model.
  - `adapters` — integrations with external artifact and analysis libraries.
  - `writers` — output traversal, rendering, and serialization.
- These areas may start as single modules, such as `composer.py` or `adapters.py`.
- As functionality grows, `adapters` and `writers` may become first-level subpackages, for example:

```text
src/report_toolkit/
├── composer.py
├── model.py
├── adapters/
│   ├── pandas.py
│   └── plotly.py
└── writers/
    ├── html.py
    └── markdown.py
```

- Avoid deeper package hierarchies unless there is a clear architectural need.
- Prefer adding modules within these first-level areas over introducing additional abstraction layers.
- Keep `composer` and `model` independent of output formats and third-party analysis libraries.
- Add third-party integrations through adapters.
- Keep format-specific traversal, rendering, and serialization inside writers.

## Development environment

- Use `uv` for dependency management and command execution.
- Run commands through the project environment, for example:
  - `uv run pytest`
  - `uv run ruff check .`
  - `uv run ruff format .`
- Do not introduce an alternative environment or dependency-management workflow unless required by the project.

## Testing

- Use `pytest`.
- Prefer a small, high-value test suite rather than exhaustive unit testing.
- Add tests for:
  - public behavior and integration between components;
  - regressions;
  - important edge cases;
  - optional integrations.
- Do not add tests for trivial implementation details.
- Prefer testing through the public API when practical.
- Optional integrations must skip cleanly when their dependency is unavailable.
- Run `make test` before considering a change complete.

## Code quality

- Use Ruff for linting and formatting.
- Run `uv run ruff check .` and `uv run ruff format .` after modifying Python code.
- Follow the existing code style and naming conventions.
- Prefer simple implementations over premature abstractions.
- Keep modules focused on their architectural responsibility.

## Dependencies

- Keep the core package lightweight.
- Avoid adding required dependencies for functionality that can reasonably remain optional.
- Third-party analysis or artifact libraries should normally be optional and isolated behind adapters.
- Do not add a new dependency when the standard library or an existing dependency provides a clear solution.

## Public API

- Treat the composer-facing API as the primary user interface.
- Prefer changes that preserve existing public behavior unless a breaking change is intentional.
- Keep rendering-specific concepts out of the composition API unless they are part of the document abstraction itself.

## Documentation

- Update user-facing documentation when public behavior or APIs change.
- Add comments or docstrings where they explain non-obvious design decisions; avoid comments that merely restate the code.

## Changelog

- Update `CHANGELOG.md` under `[Unreleased]` for relevant changes, including features, bug fixes, breaking changes, and significant documentation, dependency, packaging, or development-workflow updates.
- Use the appropriate Keep a Changelog category, such as `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, or `Security`, following the existing format.
- Keep entries concise and describe the effect on users or contributors. Include migration guidance when a change breaks existing behavior.
- Update an existing entry when refining the same change rather than adding duplicate notes. Minor typos and routine internal refactors without observable effects do not require an entry.

## Validation

For normal changes, the expected validation is:

1. `uv run pytest`
2. `uv run ruff check .`
3. `uv run ruff format --check .`
4. `make build` when the change affects packaging, dependencies, or distribution behavior.
