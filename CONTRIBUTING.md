# Contributing

Bug reports and feature requests belong in [GitHub issues](https://github.com/DisplacedForest/ha-hevy-tracker/issues). Include the Home Assistant version, integration version, steps to reproduce, and relevant logs with API keys removed.

## Setup

Install [mise](https://mise.jdx.dev/getting-started.html) and [Lefthook](https://lefthook.dev/installation/). Clone the repository and create a dedicated development branch and worktree under `.worktrees/`.

```sh
mise trust
mise install
mise run setup
lefthook install
```

The repository pins Python 3.14 and Node 24. Test dependencies include Home Assistant and its custom component test harness. `mise run setup` creates `.venv` and installs the Python and JavaScript development dependencies.

## Checks

```sh
mise run check
mise run ci
mise run security
```

`check` verifies formatting, lint, Python types, Python tests, and card tests. `ci` also compiles Python and checks the bundled card's JavaScript syntax. GitHub Actions runs these same tasks. `security` runs Semgrep and dependency audits; Semgrep uses its own Python 3.13 environment through uv.

To apply Python formatting before checking it:

```sh
.venv/bin/ruff format custom_components/hevy tests
```

The frontend is a bundled JavaScript module. It ships directly with the integration and has no separate bundle generation step. See [DEVELOPMENT.md](DEVELOPMENT.md) for Home Assistant testing.

## Pull requests

Keep each pull request focused, explain the resulting behavior, and include test evidence and documentation updates. Run `mise run check` before pushing and `mise run ci` before review. Every change goes through a pull request, green hosted checks, and independent review before a squash merge.

Changes are rejected when they break existing behavior, lack tests for meaningful behavior changes, include unrelated changes or secrets, or claim verification that was not run. Do not add source comments or docstrings, AI attribution, or em dashes. Use descriptive Conventional Commit messages.

After merging, remove the completed branch and worktree. Release changes also follow the release process in [DEVELOPMENT.md](DEVELOPMENT.md).
