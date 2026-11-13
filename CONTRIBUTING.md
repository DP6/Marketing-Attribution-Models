# Contributing to MAM

Thank you for your help making Marketing Attribution Models better! Every contribution is appreciated. There are many areas where you can contribute.

## Reporting bugs and proposing changes

- Search the [existing issues](https://github.com/DP6/Marketing-Attribution-Models/issues) first.
- Bugs: use the [bug report template](https://github.com/DP6/Marketing-Attribution-Models/issues/new?template=bug_report.md). Include the MAM version (`pip show marketing_attribution_models`), Python version, the smallest input data that reproduces the problem, what you got, and what you expected.
- Features: use the [feature request template](https://github.com/DP6/Marketing-Attribution-Models/issues/new?template=feature_request.md). Describe the problem, not just the solution.
- **Security vulnerabilities:** email koopas@dp6.com.br. Do not open a public issue.

## Development setup

Marketing Attribution Models has a lot of features and maintaining documentation takes time. If anything is unclear, or could be explained better, we appreciate the time you spend correcting or clarifying it.

There is a link in the bottom of each website page to quickly edit it.

## Issues

Before submitting the issue:

- Search the existing issues
- Provide all the relevant information, reducing both your schema and data to the smallest possible size when they still have the issue.

We value simplicity - simplifying the example that shows the issue makes it more valuable for other users. This process helps us reduce situations where an error is occurring due to incorrect usage rather than a bug.

### Bug reports

Please make sure to include the following information in the issue:

1. What version of are you using?
2. Does the issue happen if you use the latest version?
3. Schema and the data you are validating (please make it as small as possible to reproduce the issue).
5. Your code sample (please use `schema` and `data` as variables).
6. Validation result, data AFTER validation, error messages.
7. What results did you expect?

[Create bug report](https://github.com/DP6/Marketing-Attribution-Models/issues/new?template=bug_report.md).

### Security vulnerabilities

To report a security vulnerability, please use the e-mail koopas@dp6.com.br.

Please do NOT report security vulnerabilities via GitHub issues.

### <a name="changes"></a>Change proposals

[Create a proposal](https://github.com/DP6/Marketing-Attribution-Models/issues/new?template=feature_request.md) for a new feature, option or some other improvement.

Please include this information:

1. The version you are using.
2. The problem you want to solve.
3. Your solution to the problem.
4. Would you like to implement it?

If you’re requesting a change, it would be helpful to include this as well:

1. What you did.
2. What happened.
3. What you would like to happen.

Please include as much details as possible - the more information, the better.

### <a name="installation"></a>Installation and dependency issues

[Create an issue](https://github.com/DP6/Marketing-Attribution-Models/issues/new?template=bug_report.md) to report problems that happen during Marketing Attribution Models installation or when Marketing Attribution Models is missing some dependency.

Before submitting the issue, please try the following:

- use the latest stable Node.js and `npm`
- try using `yarn` instead of `npm` - the issue can be related to https://github.com/npm/npm/issues/19877
- remove `node_modules` and `package-lock.json` and run `npm install` again

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
