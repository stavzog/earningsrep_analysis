# Project Roadmap

This is a suggested path through the project, not a gated plan. The team can
reorder, combine, or replace actions as the work evolves. GitHub Issues are the
record of specific work and decisions; update issue links and this roadmap as
the plan changes. Follow
[`AI_ASSISTED_PROJECT_WORKFLOW.md`](AI_ASSISTED_PROJECT_WORKFLOW.md) for issue
templates, agent use, pull requests, and review.

## Agreed project direction

- **Question:** Can changes in management's tone between earnings calls predict
  whether the stock beats the market on the event trading day?
- **Benchmark and target:** Compare the stock return with the equal-weight S&P
  500 ETF (`RSP`) return on the event trading day; classify the stock as UP or
  DOWN relative to RSP.
- **Event-day timing:** Calls before 09:30 ET map to that trading date; calls
  after 16:00 ET map to the next trading date. Whether to exclude calls during
  market hours is not decided.
- **Features and models:** The deck specifies 15 FinBERT sentiment inputs
  (five per call section) plus EPS, with about 128-token sentence-preserving
  chunks. Compare the stated baselines, two feedforward networks, and a GRU
  using the last four calls.
- **Chronological split:** Train 2015–2022, validate 2023, and test 2024–2025.
- **Primary evaluation metric:** Directional accuracy on the held-out test set.

These choices are also recorded in `HANDOFF.md`. Some details remain open; they
do not prevent independent exploration or data loading. Use the action and
amendment workflow below when an open decision affects the work at hand.

## Action and amendment workflow

- **Choose an action:** Pick the next useful, scoped task from this roadmap or
  another team priority. The roadmap's order is a suggestion, not a dependency
  rule.
- **Start with what is known:** Create or update the relevant GitHub Issue with
  the goal, expected result, current assumptions, and questions that may arise.
  Proceed on work that does not require those answers.
- **Propose an amendment when needed:** If new evidence or an unresolved choice
  changes the scope or method, document the question, evidence, options, and a
  recommendation in the issue. Pause only the affected decision, not unrelated
  work.
- **Record the team decision:** Once discussed, update the issue and, for a
  project-wide decision, `HANDOFF.md`. Amend the task plan and continue.
- **Close the loop:** In the PR, summarize the action taken, amendments accepted
  or rejected, checks run, and any remaining questions.

## Suggested roadmap

| Suggested order | Action | Type | Tracking |
| --- | --- | --- | --- |
| Current | Keep the handoff aligned with the pitch deck and maintain this roadmap | Chore | [Issue #5](https://github.com/stavzog/earningsrep_analysis/issues/5) · [PR #6](https://github.com/stavzog/earningsrep_analysis/pull/6) |
| Next | Load and inspect transcript, company-price, and RSP data | Feature | Create an issue when ready |
| Later | Explore and implement call-to-trading-day alignment and stock-versus-RSP labels | Feature / experiment | Scope as evidence and decisions emerge |
| Later | Parse call sections and extract/cache FinBERT chunk scores | Feature | Scope from data inspection |
| Later | Assemble model inputs and chronological train/validation/test examples | Feature | Refine as feature choices are amended |
| Later | Run the deck's baseline and neural-model comparisons | Experiment | Agree on exact configurations in the relevant issues |
| Later | Evaluate the held-out test set and report findings and limitations | Experiment | Update based on results |

### Next action: load and inspect the data

The data-loading stage can begin without settling every label or feature
question. A useful first issue could cover:

1. Load the transcript dataset and inspect its schema, date coverage, empty
   records, duplicate calls, and availability of call times and speaker
   segments.
2. Download adjusted daily price history for a small sample of company tickers
   and `RSP`; inspect ticker mapping, date coverage, missing prices, and
   download failures.
3. Keep downloaded data and caches in ignored local data directories. Do not
   commit raw or processed datasets.
4. Produce a concise data inventory and document the exact load commands,
   configuration, and any coverage limitations so the team can decide the next
   action from observed evidence.

## Open questions to resolve along the way

These questions are reminders for the action/amendment workflow, not
prerequisites for starting unrelated work. Record an answer in the relevant
issue and update `HANDOFF.md` when it becomes a project-wide decision.

- **Event timing:** confirm the transcript timezone; decide whether to exclude
  calls from 09:30–16:00 ET; define handling for calls exactly at 09:30 or
  16:00, missing times, weekends, and holidays.
- **Return label:** specify the stock and RSP return calculation and price
  fields, and define what happens when returns are equal.
- **Sentiment inputs:** define the five values per section and how average and
  worst-chunk scores are aggregated.
- **Other inputs:** choose the EPS value, missing-EPS handling, and the
  management-tone feature used for FFN-B and the tone-change baseline; decide
  whether and how Loughran–McDonald features are used.
- **Sequences:** decide how to handle calls with fewer than four usable calls
  in their history.
- **Evaluation:** confirm which model comparisons define success and whether
  secondary metrics or uncertainty estimates are required.

## Issue and pull-request practices

- Create scoped GitHub Issues from the feature, experiment, or chore template.
  Each issue needs a goal, plan, out-of-scope statement, and a concrete
  definition of done (or a hypothesis and results plan for an experiment).
- Keep each issue and PR reviewable. Link the PR with `Closes #<issue-number>`.
- Review and understand the changes yourself; request a teammate to review.
  The PR author must not approve their own PR.
- Record what was built, how it was checked, and the AI tools used in the issue
  and PR. Update this roadmap's suggestions and links as the team's plan changes.
