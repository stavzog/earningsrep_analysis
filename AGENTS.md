# Agent instructions

## Project context

This is a university ML project exploring whether the language and tone changes
in earnings-call transcripts can predict stock returns. The repository's
current research plan, data sources, labeling decisions, model comparisons, and
items still requiring verification are documented in [`HANDOFF.md`](HANDOFF.md).
Read it before making project or modeling decisions.

The repository currently contains project documentation and GitHub workflow
templates. Inspect the files and available tooling before assuming that a model
implementation, dependencies, or test commands already exist.

## Working from issues

- Work on one GitHub issue at a time and stay within its stated scope.
- Use the feature, experiment, or chore issue template that matches the work.
- If an issue conflicts with `HANDOFF.md`, or depends on an `[OPEN]` or
  `[VERIFY]` item, surface the conflict or question before proceeding; do not
  silently choose an answer.
- Use a topic branch and a pull request targeting `main`. Link the issue with
  `Closes #<issue-number>`. Do not push directly to `main`; request review from
  someone other than the PR author.
- Report files changed, checks run and their outcomes, and any checks not run.
  Do not claim a test or experiment passed unless it was actually run.

## Data and research safeguards

- Do not commit downloaded transcripts, stock-price data, intermediate or
  processed datasets, model outputs, checkpoints, caches, credentials, or
  other private data. Keep local data in the ignored project data directories.
- Follow the datasets' licenses and the team's data-handling requirements.
- Preserve the time-based evaluation split and avoid look-ahead leakage. Fit
  preprocessing, feature transformations, and other learned parameters using
  training data only, as specified in `HANDOFF.md`.
- Keep experiments reproducible: record the configuration, random seed where
  applicable, data/split choices, and commands used.

## Commands and dependencies

No project-specific install, run, or test commands are established yet. Inspect
the repository for the current source of truth before running commands; when
adding a development workflow, document the verified commands in the project
documentation rather than guessing.
