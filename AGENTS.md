# Working on Hevy Workout Tracker

Keep changes focused and track requests in GitHub issues. This project does not use Linear. Use a dedicated branch and worktree for development, with worktrees under `.worktrees/`.

Do not add source comments or docstrings. Do not use em dashes in code, documentation, commits, or pull requests. Keep user-facing text plain and specific.

## Local verification

Install the toolchain with `mise install`, then run `mise run setup`. Install the Git hooks with `lefthook install`.

- `mise run check`: check Python formatting, Ruff lint, integration types, Python tests, and card tests.
- `mise run ci`: run the same checks as GitHub Actions, including Python compilation and card syntax validation.
- `mise run security`: run Semgrep and Python and JavaScript dependency audits.

Run `mise run check` before every push and `mise run ci` before requesting review. Fix the cause of failing checks. Report environment blocks separately from code failures.

## Completion

A change is complete when its acceptance criteria are met, `mise run check` and `mise run ci` pass, every hosted pull request check passes, and an independent reviewer approves the diff. Keep review evidence on the GitHub pull request. Use a squash merge and delete the merged branch and completed worktree.

## Releases

Update the integration version and changelog together. Before publishing a release, verify the merged commit's CI, exercise the integration and card in a local Home Assistant instance with fixture data, and review the release notes. Tag the version and publish its GitHub release for HACS.

Report fixture-based Home Assistant checks separately from writes to a real Hevy account. If no real write was exercised, say so in the release handoff. Do not present fixture results as a verified production write.
