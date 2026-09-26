# Repository guide

- Source code lives in `src/reportkit/`; tests live in `tests/`.
- Run `make test` for unit and installed-library integration tests.
- Run `make build` to produce distribution archives (requires `build`).
- Keep composition in `composer.py` and the document model in `model.py` independent of HTML and third-party analysis libraries.
- Add artifact integrations through `adapters.py`, and HTML traversal and styling through `writer.py`.
- Add tests for new behavior. Optional integrations should skip cleanly when their dependency is absent.
