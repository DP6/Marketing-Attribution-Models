# CHANGELOG


## v2.0.0 (2026-09-01)

### Bug Fixes

- Black formatting on root scripts and codigo_legado
  ([`c967529`](https://github.com/DP6/Marketing-Attribution-Models/commit/c9675299acea8457683d41d36a83ab7358357ead))

### Code Style

- Format code using black to comply with CI lint
  ([`5e57334`](https://github.com/DP6/Marketing-Attribution-Models/commit/5e57334546a7d907721dda15d703cd0c6202b462))

### Continuous Integration

- Configure Trusted Publisher workflow for PyPI v2.0.0 release
  ([`59de4e9`](https://github.com/DP6/Marketing-Attribution-Models/commit/59de4e94d9a487fa6b6b4d8081f96f215c0eb21a))

- Upgrade to python-semantic-release@v9 with OIDC-based PyPI publish - Add permissions:
  contents:write, id-token:write - Add pypa/gh-action-pypi-publish step (no token needed, uses
  Trusted Publisher) - Add build_command to semantic_release config

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Features

- Add support for revenue-based attribution in preprocessing, core, models, and reporting
  ([`b0e7a6d`](https://github.com/DP6/Marketing-Attribution-Models/commit/b0e7a6dfd6c545b5bf2415e57424ab621c8faf68))

- Migração e reescrita arquitetural para Nova MAM (v2.0.0)
  ([`bd815ef`](https://github.com/DP6/Marketing-Attribution-Models/commit/bd815ef941880a43bb5ee6196d75977cb1e3c3b0))

BREAKING CHANGE: API completamente reescrita com Polars. O import path mudou de `from
  marketing_attribution_models.MAM import MAM` para `from mam.core import MAM`. Requer Python
  >=3.12.

- Migração e reescrita arquitetural para Nova MAM (v2.0.0)
  ([`3b1066b`](https://github.com/DP6/Marketing-Attribution-Models/commit/3b1066bc93d3845c1cc094c7c4883eb91e049d72))

- Substitui toda a estrutura antiga pelo código otimizado com Polars e novos modelos.

- Preserva o código legado da v1 na pasta codigo_legado/ para referência.

- Atualiza testes unitários, documentação (README.md, manifesto), design system e guias de
  modelagem.


## v1.0.11 (2026-04-27)

### Bug Fixes

- Adjusts style for comments in test
  ([`097226d`](https://github.com/DP6/Marketing-Attribution-Models/commit/097226d828d9a4df856c1a4b4cb86558d377f816))

- Ads comments to ignore the check of assert use in test file
  ([`6d68041`](https://github.com/DP6/Marketing-Attribution-Models/commit/6d680411aa84c10d0592fbf3e100877a777fda41))

- Corrige a versão do plt.style de seaborn_white para seaborn-v0_8-white
  ([`947dda8`](https://github.com/DP6/Marketing-Attribution-Models/commit/947dda8751763482060c5311a8aa6c82cad67418))

- Corrige tipo do build_command no pyproject.toml para string
  ([`27503a4`](https://github.com/DP6/Marketing-Attribution-Models/commit/27503a4a02a16a7459831b0584fbaa89b7617514))

- Seaborn style problem
  ([`88c2b02`](https://github.com/DP6/Marketing-Attribution-Models/commit/88c2b02fe4719a6422f61a07fc8fc7160d445839))

### Chores

- Manual release version 1.0.9
  ([`2c6508c`](https://github.com/DP6/Marketing-Attribution-Models/commit/2c6508c3a5b5ff9c1ec42a9cd98b778728b390ea))

- Manual release version 1.0.9
  ([`561080c`](https://github.com/DP6/Marketing-Attribution-Models/commit/561080c145352b58586a5ce849414a4f63525141))

### Documentation

- Adiciona exemplo de uso do parâmetro conversion_value_as_frequency do markov [skip ci]
  ([`4ade259`](https://github.com/DP6/Marketing-Attribution-Models/commit/4ade25930b18a158a839cd85d67ce48a509eb429))


## v1.0.10 (2022-06-09)

### Build System

- **deps**: Bump actions/checkout from 2 to 3
  ([`d11837f`](https://github.com/DP6/Marketing-Attribution-Models/commit/d11837f63cefe86bdb5608f74aace02bd1a870a2))

Bumps [actions/checkout](https://github.com/actions/checkout) from 2 to 3. - [Release
  notes](https://github.com/actions/checkout/releases) -
  [Changelog](https://github.com/actions/checkout/blob/main/CHANGELOG.md) -
  [Commits](https://github.com/actions/checkout/compare/v2...v3)

--- updated-dependencies: - dependency-name: actions/checkout dependency-type: direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

- **deps**: Bump actions/checkout from 2 to 3
  ([`27c5e09`](https://github.com/DP6/Marketing-Attribution-Models/commit/27c5e0933494c90aa31644dd8a03057755c57541))

Bumps [actions/checkout](https://github.com/actions/checkout) from 2 to 3. - [Release
  notes](https://github.com/actions/checkout/releases) -
  [Changelog](https://github.com/actions/checkout/blob/main/CHANGELOG.md) -
  [Commits](https://github.com/actions/checkout/compare/v2...v3)

--- updated-dependencies: - dependency-name: actions/checkout dependency-type: direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

- **deps**: Bump actions/setup-python from 2 to 3.1.0
  ([`ebba39a`](https://github.com/DP6/Marketing-Attribution-Models/commit/ebba39ab3079dc8ef2d4d511d39d4f143263344b))

Bumps [actions/setup-python](https://github.com/actions/setup-python) from 2 to 3.1.0. - [Release
  notes](https://github.com/actions/setup-python/releases) -
  [Commits](https://github.com/actions/setup-python/compare/v2...v3.1.0)

--- updated-dependencies: - dependency-name: actions/setup-python dependency-type: direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

- **deps**: Bump codacy/codacy-analysis-cli-action from 3.0.3 to 4.0.2
  ([`d76147a`](https://github.com/DP6/Marketing-Attribution-Models/commit/d76147aa81905f1615aeeeb1148b88f74f6ada06))

Bumps [codacy/codacy-analysis-cli-action](https://github.com/codacy/codacy-analysis-cli-action) from
  3.0.3 to 4.0.2. - [Release notes](https://github.com/codacy/codacy-analysis-cli-action/releases) -
  [Commits](https://github.com/codacy/codacy-analysis-cli-action/compare/3.0.3...4.0.2)

--- updated-dependencies: - dependency-name: codacy/codacy-analysis-cli-action dependency-type:
  direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

- **deps-dev**: Bump pytest from 6.2.5 to 7.1.1
  ([`57dc7a1`](https://github.com/DP6/Marketing-Attribution-Models/commit/57dc7a1d1593f1841ff7d6d5cbac9a6f5a284565))

Bumps [pytest](https://github.com/pytest-dev/pytest) from 6.2.5 to 7.1.1. - [Release
  notes](https://github.com/pytest-dev/pytest/releases) -
  [Changelog](https://github.com/pytest-dev/pytest/blob/main/CHANGELOG.rst) -
  [Commits](https://github.com/pytest-dev/pytest/compare/6.2.5...7.1.1)

--- updated-dependencies: - dependency-name: pytest dependency-type: direct:development

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

- **deps-dev**: Bump pytest from 7.1.1 to 7.1.2
  ([`f06d7f2`](https://github.com/DP6/Marketing-Attribution-Models/commit/f06d7f25444d23c027b886cc1615d6e459fec684))

Bumps [pytest](https://github.com/pytest-dev/pytest) from 7.1.1 to 7.1.2. - [Release
  notes](https://github.com/pytest-dev/pytest/releases) -
  [Changelog](https://github.com/pytest-dev/pytest/blob/main/CHANGELOG.rst) -
  [Commits](https://github.com/pytest-dev/pytest/compare/7.1.1...7.1.2)

--- updated-dependencies: - dependency-name: pytest dependency-type: direct:development

update-type: version-update:semver-patch ...

Signed-off-by: dependabot[bot] <support@github.com>

### Code Style

- :art: Black formatter
  ([`2bbe9e6`](https://github.com/DP6/Marketing-Attribution-Models/commit/2bbe9e6330f66822a160e2829cca50feb926c2d9))

- :art: pylint on pytest
  ([`e270474`](https://github.com/DP6/Marketing-Attribution-Models/commit/e270474f1461c8b4123aa08d9ae3d1cf92449829))

- Refactor import
  ([`3a060c2`](https://github.com/DP6/Marketing-Attribution-Models/commit/3a060c26fb1742019183f42ecd7f3a9c9fb55142))

- Reformatting code
  ([`6eabac0`](https://github.com/DP6/Marketing-Attribution-Models/commit/6eabac0454ddaea665ae4553fb10bbfeb23d8e2f))

Commit black code reformatting.

- Style hotfix
  ([`821c8ee`](https://github.com/DP6/Marketing-Attribution-Models/commit/821c8ee2762f6f1056c849334bce7316b9d52ce9))

### Continuous Integration

- :construction_worker: Add semantic-release
  ([`5974332`](https://github.com/DP6/Marketing-Attribution-Models/commit/5974332094348d9247a6213c127e466755dfc8ad))

adjusted encoding and version

- :construction_worker: Added codacy analysis
  ([`dbb2a5b`](https://github.com/DP6/Marketing-Attribution-Models/commit/dbb2a5b927e60297d333fc2bcfea7f7f37b9b848))

- :construction_worker: added toml file
  ([`d315a00`](https://github.com/DP6/Marketing-Attribution-Models/commit/d315a000f12730556d4c7b514b7eff9c4b35ac32))

- :green_heart: Adjusted config pyproject and actions
  ([`fc086f9`](https://github.com/DP6/Marketing-Attribution-Models/commit/fc086f9eb3ac6a0a7939d8d6760c3912c0cb92c7))

### Documentation

- :memo: Added codacy
  ([`1504574`](https://github.com/DP6/Marketing-Attribution-Models/commit/15045744dddfd10a29e18f38bbd18d90e8bbff87))

### Refactoring

- Fixed some pylint warnings
  ([`91da853`](https://github.com/DP6/Marketing-Attribution-Models/commit/91da853a859ddd1c9ae03c9e2b930106c4207bcd))

- Fixed some pylint warnings
  ([`29aada7`](https://github.com/DP6/Marketing-Attribution-Models/commit/29aada7be4b24bc0802f4dbcfb45a0329c0dc036))

- Fixed some pylint warnings
  ([`277b1d9`](https://github.com/DP6/Marketing-Attribution-Models/commit/277b1d95206a111d7fdb95ad0820f810a16347f1))

- **random_df**: Ajusting formatting
  ([`5421be3`](https://github.com/DP6/Marketing-Attribution-Models/commit/5421be3edca3fdc29046638d2936ab5618f609c5))

- **random_df**: Ajusting formatting
  ([`226b321`](https://github.com/DP6/Marketing-Attribution-Models/commit/226b3213bef7d2d8104c6dce248a428ad922d25c))

- **random_df**: Ajusting formatting and removing lint warnings
  ([`bd94ec2`](https://github.com/DP6/Marketing-Attribution-Models/commit/bd94ec232a65c5d348785ab2cca16b9a1a546ec2))

- **random_df**: Ajusting formatting and removing lint warnings
  ([`29377fa`](https://github.com/DP6/Marketing-Attribution-Models/commit/29377fa9ef3bfa6426d942239b2359e9659a6c16))

### Testing

- :sparkles: pytest implementation
  ([`882abc2`](https://github.com/DP6/Marketing-Attribution-Models/commit/882abc22b1b8f28b9d5b13df85a7890d19b615b4))

- :white_check_mark: create test_mam for future pytest
  ([`1883ab0`](https://github.com/DP6/Marketing-Attribution-Models/commit/1883ab0fdea8f0f2499cfe9e09107933476cbe9f))

- :white_check_mark: create test_mam for future pytest
  ([`8f56835`](https://github.com/DP6/Marketing-Attribution-Models/commit/8f56835dfd52f70357fe02d82ecdf694b4f650f0))


## v1.0.8 (2021-03-23)

### Code Style

- :lipstick: Ajutilizado tabelas para HTML
  ([`0f8a9bd`](https://github.com/DP6/Marketing-Attribution-Models/commit/0f8a9bd33a20881a64fbde6ea6a613ed64d0f4e0))

- Implementing black code formatter
  ([`06b8541`](https://github.com/DP6/Marketing-Attribution-Models/commit/06b854190e1c96610bf88e678c65871b44e852eb))

### Documentation

- :memo: Adicionado template git e tema padrão
  ([`7f0b40a`](https://github.com/DP6/Marketing-Attribution-Models/commit/7f0b40ab98afed6f7cc2142e6ffeb4731334c8df))
