# Contributing to eyeroll

Thanks for your interest in contributing! Here's how to get started.

## Development setup

```bash
git clone https://github.com/mnvsk97/eyeroll.git
cd eyeroll
pip install -e '.[dev,all]'
```

Or with uv:

```bash
uv sync
```

## Running tests

```bash
pytest                                                # unit tests
pytest --cov --cov-report=term-missing                # with coverage
pytest tests/test_backend.py -v                       # single test file
pytest tests/test_integration.py -v -m integration    # integration tests (requires API keys)
```

Integration tests hit real APIs and are skipped in CI. Run them manually before submitting changes to backend or analysis code.

## Making changes

1. Fork the repo and create a branch from `main` (use `feat/your-feature` or `fix/your-fix`)
2. Make your changes
3. Add or update tests as needed
4. Run `pytest` and make sure all tests pass
5. Open a pull request

CI runs tests on Python 3.11, 3.12, and 3.13 against all PRs.

## Code style

- Keep it simple — no over-engineering
- Mock all API calls in tests — never hit external services in unit tests
- Follow existing patterns in the codebase
- No linter enforced — just match what's already there

## What to work on

- Check [open issues](https://github.com/mnvsk97/eyeroll/issues) for bugs or feature requests
- Backend improvements (Gemini, OpenAI, Ollama)
- New video source support
- Better frame extraction heuristics
- Documentation improvements

For deeper context on architecture, testing patterns, and design decisions, see the [development docs](https://mnvsk97.github.io/eyeroll/development/).

## Reporting bugs

Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Backend and Python version

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
