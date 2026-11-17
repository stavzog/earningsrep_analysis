# Project Roadmap

This roadmap turns the current pitch deck and [`HANDOFF.md`](HANDOFF.md) into
trackable work. GitHub Issues are the source of truth for assignments,
discussion, and completion; update the issue links and statuses here as work
moves forward. Follow [`AI_ASSISTED_PROJECT_WORKFLOW.md`](AI_ASSISTED_PROJECT_WORKFLOW.md)
for issue templates, agent use, pull requests, and review.

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

These choices are also recorded in `HANDOFF.md`. Do not implement unresolved
details by guessing; settle them with the team and update the handoff first.

## Roadmap and tracking

Statuses: **In progress** = being scoped or decided; **Blocked** = depends on an
earlier decision or deliverable; **Not started** = ready after dependencies.
Issue numbers and PRs should be added when the team creates them.

| Order | Work item | Type | Depends on | Status | GitHub issue |
| --- | --- | --- | --- | --- | --- |
| 0 | Record agreed methodology and outstanding decisions in `HANDOFF.md` | Chore | — | In progress; documentation PR pending | [#5](https://github.com/stavzog/earningsrep_analysis/issues/5) |
| 1 | Build transcript and price loading plus event-day alignment and RSP labels | Feature | 0 | Blocked | — |
| 2 | Split calls into sections and extract/cache FinBERT chunk features | Feature | 0 | Blocked | — |
| 3 | Build the 16-input call records, four-call sequences, and date-based splits | Feature | 1, 2 | Blocked | — |
| 4 | Implement and evaluate the agreed baseline models | Experiment | 3 | Blocked | — |
| 5 | Train and compare FFN-A, FFN-B, and the GRU | Experiment | 4 | Blocked | — |
| 6 | Run the held-out test evaluation and summarize findings and limitations | Experiment | 5 | Blocked | — |

## Decisions to settle before implementation

Record each answer in `HANDOFF.md` and the relevant GitHub issue.

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

## Issue and pull-request rules

- Create scoped GitHub Issues from the feature, experiment, or chore template.
  Each issue needs a goal, plan, out-of-scope statement, and a concrete
  definition of done (or a hypothesis and results plan for an experiment).
- Work on one issue per branch and PR. Link the PR with `Closes #<issue-number>`.
- Review and understand the changes yourself; request a teammate to review.
  The PR author must not approve their own PR.
- Record what was built, how it was checked, and the AI tools used in the issue
  and PR. Update this roadmap's status and links after the issue is completed.
