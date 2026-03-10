# Contributing to AgentUQ

Thanks for contributing. This project keeps the contributor workflow intentionally small: make a focused change, run the relevant tests, and open a pull request with enough context to review it quickly.

## Before you start

- Search existing issues and pull requests to avoid duplicate work.
- Prefer small, focused pull requests over broad refactors.
- If you are changing behavior, tests and docs should move with the code.

## Development setup

AgentUQ is a Python package. The standard local setup is:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

The documentation site is optional and only needed when you are working on docs navigation, layout, or the Docusaurus app under `website/`.

## Project layout

- `src/agentuq`: library code
- `tests`: unit, contract, and opt-in live tests
- `docs`: canonical documentation content
- `website`: Docusaurus site
- `examples`: runnable usage examples

## Running tests

Default test runs stay offline:

```bash
python -m pytest
```

Live smoke tests are opt-in and require the relevant API keys in your environment:

```bash
AGENTUQ_RUN_LIVE=1 python -m pytest -m live
```

If your change only touches docs or website styling, run the checks that are relevant to that work.

## Working on docs

- Edit the canonical docs in `docs/`.
- Use `website/` when you need to change the site shell, theme, navigation, or build configuration.
- If you need a local docs preview:

```bash
cd website
npm install
npm run dev
```

For a production-style docs build:

```bash
cd website
npm run build
```

## Pull requests

When opening a pull request:

- Explain what changed and why.
- Call out any behavior changes or compatibility risks.
- Link the relevant issue when there is one.
- Include tests or explain why tests were not needed.
- Update docs when public behavior, examples, or contributor workflow changes.

## Style expectations

- Keep changes targeted and readable.
- Match the surrounding code style instead of introducing a new pattern.
- Avoid unrelated cleanup in the same pull request.

## License

By submitting a contribution, you agree that your work will be licensed under the project license in [`LICENSE.txt`](LICENSE.txt).
