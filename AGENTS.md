# Agent instructions

## Project context

This is a university ML project exploring whether the language and tone changes
in earnings-call transcripts can predict stock returns. All project details appear in [`HANDOFF.md`](HANDOFF.md). Read it before making project or modeling decisions.

The repository contains project documentation and GitHub workflow
templates. Inspect the files and available tooling before assuming that a model
implementation, dependencies, or test commands already exist.

## Working from issues

- Stay within its stated scope. Do not do more than you are asked to do.
- The issues are the paper trail, but the user's prompt and the conversation is what defines the task.
- Use the feature, experiment, or chore issue template that matches the work.
- If an issue conflicts with `HANDOFF.md`, or depends on an `[OPEN]` or
  `[VERIFY]` item, surface the conflict or question before proceeding.
- do not  silently choose an answer.
- Use a topic branch and a pull request targeting `main`. Link the issue with
  `Closes #<issue-number>`. Do not push directly to `main`; request review from  someone other than the PR author.
- Report files changed, checks run and their outcomes, and any checks not run.
  Do not claim a test or experiment passed unless it was actually run.

## Agent Behavior and Guidelines

# GLOBAL AGENT BEHAVIOR & RULES

1. **READ-ONLY BY DEFAULT:** Do not be overly eager to implement. If the user asks you to "read", "review", "brainstorm", or "familiarize" yourself with a project or file, you must ONLY read and discuss. Do NOT start writing code or implementing features you see.
2. **IGNORE PENDING TASKS:** If you see a "TODO" or "Pending Tasks" list in a markdown file or codebase, acknowledge it, but DO NOT execute any of the tasks unless explicitly commanded to do so.
3. **WAIT FOR THE GREEN LIGHT:** During brainstorming or file review, prefer outputting clean code snippets directly in the chat. Do NOT use the `write` or `edit` tools to modify files until the user explicitly gives a clear green light (e.g., "implement it", "write the code", "save this").
4. **SCOPE CONTROL:** When explicitly asked to implement a feature, implement ONLY that feature. Do not preemptively rewrite unrelated files or build out the entire application.

## Data and research safeguards

- Do not commit downloaded transcripts, stock-price data, intermediate or
  processed datasets, model outputs, checkpoints, caches, credentials, or
  other private data. Keep local data in the ignored project data directories.
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
