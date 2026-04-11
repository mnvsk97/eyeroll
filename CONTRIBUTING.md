# Contributing to eyeroll

## Setup

```bash
git clone https://github.com/mnvsk97/eyeroll.git
cd eyeroll
uv sync  # or: pip install -e '.[dev,all]'
```

## Rules

1. **Run everything locally before opening a PR.** All tests must pass on your machine.
2. **Keep it minimal.** No over-engineering, no unnecessary abstractions, no bloat.
3. **No Opus.** Use Sonnet or Haiku for any AI-assisted work. Opus is not allowed.
4. **Mock all API calls in tests.** Never hit external services in unit tests.
5. **Match existing patterns.** No linter enforced — just follow what's already there.
6. **Test your changes.** Add or update tests for anything you touch.

## Workflow

1. Fork and branch from `main` (`feat/thing` or `fix/thing`)
2. Make changes
3. Run `pytest` locally — all tests must pass
4. Test manually with a real video/screenshot
5. Open a PR using the template

CI runs on Python 3.11, 3.12, 3.13.

## What to work on

Check [open issues](https://github.com/mnvsk97/eyeroll/issues) or see the [dev docs](https://mnvsk97.github.io/eyeroll/development/).

## License

By contributing, you agree your work is licensed under MIT.
