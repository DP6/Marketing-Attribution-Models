# Contributing to MAM

Thanks for helping improve MAM (Marketing Attribution Models)! For anything bigger than a small fix, please [open an issue](https://github.com/DP6/Marketing-Attribution-Models/issues/new/choose) first so we can agree on the approach before you write code.

## Reporting bugs and proposing changes

- Search the [existing issues](https://github.com/DP6/Marketing-Attribution-Models/issues) first.
- Bugs: use the [bug report template](https://github.com/DP6/Marketing-Attribution-Models/issues/new?template=bug_report.md). Include the MAM version (`pip show marketing_attribution_models`), Python version, the smallest input data that reproduces the problem, what you got, and what you expected.
- Features: use the [feature request template](https://github.com/DP6/Marketing-Attribution-Models/issues/new?template=feature_request.md). Describe the problem, not just the solution.
- **Security vulnerabilities:** email koopas@dp6.com.br. Do not open a public issue.

## Development setup

Requires Python 3.8+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pip install black
```

Before pushing:

```bash
pytest          # tests
black .         # formatting - CI runs `black . --check` and blocks merges on failure
```

## Pull requests

1. Branch off `master` (e.g. `fix/explode-memory`, `feat/mam-file-format`).
2. Keep the change focused; avoid unrelated refactors or reformatting.
3. Add or update tests in `tests/` for any behavior change.
4. Make sure `pytest` and `black . --check` pass.
5. Open the PR against `master` and fill in the template. It needs 2 approvals and a green `lint` check to merge.

## Commit messages (this decides the release)

Releases are fully automated with [python-semantic-release](https://python-semantic-release.readthedocs.io/). The **commit messages** on `master` decide whether a new version is published and which number it gets, so they must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(optional scope): short description
```

| Type | Example | Release |
|---|---|---|
| `fix` | `fix: select only used columns before explode` | patch (2.1.1 -> 2.1.2) |
| `perf` | `perf(markov): count transitions without list copies` | patch |
| `feat` | `feat: MAM.load reads .mam files` | minor (2.1.1 -> 2.2.0) |
| `feat!` / `fix!`, or a `BREAKING CHANGE:` footer | `feat!: drop pandas input support` | major (2.1.1 -> 3.0.0) |
| `docs`, `style`, `test`, `refactor`, `ci`, `build`, `chore` | `docs: document the .mam file format` | no release |

A message without a type (e.g. `ajustes no pyproject`) is ignored: if every commit in a PR looks like that, **no version is released**. If you squash-merge, the PR title becomes the commit message, so it must follow the same format.

## How releases work

Nothing is done by hand. On every push to `master`, the `Semantic Release` workflow:

1. Reads the commits since the last `vX.Y.Z` tag and works out the next version.
2. Pushes the `vX.Y.Z` tag and creates a GitHub Release with the release notes.
3. Builds the package with that version.
4. Publishes to [PyPI](https://pypi.org/project/marketing_attribution_models/) via Trusted Publishing.

The **git tag** is the only place the version is stored. `pyproject.toml` has no hardcoded version: [setuptools-scm](https://setuptools-scm.readthedocs.io/) reads it from the tag at build time (a build from an untagged commit gets a dev version such as `2.2.1.dev3+g1a2b3c4`). Never create `v*` tags by hand. Release notes are on [GitHub Releases](https://github.com/DP6/Marketing-Attribution-Models/releases).

## License

By contributing, you agree that your contribution is licensed under the [Apache-2.0 License](LICENSE) used by this project.
