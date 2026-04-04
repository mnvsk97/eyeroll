# Contributing to eyeroll

Thanks for your interest in contributing! Here's how to get started.

## Development setup

```bash
git clone https://github.com/mnvsk97/eyeroll.git
cd eyeroll
pip install -e '.[dev,all]'
```

## Running tests

```bash
pytest                                                # unit tests (144 tests)
pytest --cov --cov-report=term-missing                # with coverage
pytest tests/test_integration.py -v -m integration    # integration tests (requires API keys)
```

Integration tests hit real APIs and are skipped in CI. Run them manually before submitting changes to backend or analysis code.

## Making changes

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Add or update tests as needed
4. Run `pytest` and make sure all tests pass
5. Open a pull request

## What to work on

- Check [open issues](https://github.com/mnvsk97/eyeroll/issues) for bugs or feature requests
- Backend improvements (Gemini, OpenAI, Ollama)
- New video source support
- Better frame extraction heuristics
- Documentation improvements

## Code style

- Keep it simple — no over-engineering
- Mock all API calls in tests — never hit external services in unit tests
- Follow existing patterns in the codebase

## Reporting bugs

Open an issue at https://github.com/mnvsk97/eyeroll/issues with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Backend and Python version

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
