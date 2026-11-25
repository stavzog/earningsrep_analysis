# Project Handoff: Earnings Call Tone and Next-Day Market Performance

Context for the coding agent. This is a university ML class project. The current pitch deck is the source of truth for the revised project direction. Decisions that still need team agreement are marked **[OPEN]**; details to confirm from the data or tools are marked **[VERIFY]**. Do not silently turn open questions into assumptions.

---

## 1. Research question

**Can shifts in management's tone between earnings calls predict whether a stock beats the market on the next relevant trading day?**

Formal objective: use earnings-call language and tone features to predict whether the company's stock return is higher or lower than the market benchmark's return on the event trading day. Compare a current-call feedforward model, a feedforward model with an explicit tone-change input, and a GRU that reads a sequence of recent calls.

Expected outcome: direction is hard to predict because markets are efficient. A modest result is acceptable; the priority is a clean, fair comparison using the same examples and chronological splits (§7–8).

---

## 2. Data sources

| Data | Source | Notes |
|---|---|---|
| Earnings call transcripts | Hugging Face `kurry/sp500_earnings_transcripts` | 33,362 rows, 685 companies, 2005-10 to 2025-05, Parquet, ~1.8 GB, single `train` split |
| Daily stock prices | `yfinance` | Use adjusted prices (`auto_adjust=True`) so splits and dividends don't create fake returns |
| Market benchmark | `yfinance` ticker `RSP` (equal-weight S&P 500 ETF) | Compare the stock return with RSP's return |
| EPS actual vs. estimate | `yfinance` `Ticker.get_earnings_dates(limit=...)` → `EPS Estimate`, `Reported EPS`, `Surprise(%)` | `limit=100` reaches back to the early 2000s; 98.1% of eligible events match an EPS row (see [`DATA_INVENTORY.md`](DATA_INVENTORY.md#eps-coverage)) |
| Sentiment model | Hugging Face `ProsusAI/finbert` | Pre-trained and frozen; use chunk-level positive/negative/neutral probabilities |
| Keyword dictionary | Loughran–McDonald Master Dictionary (Notre Dame SRAF) | Positive / Negative / Uncertainty word lists; role in the model comparison is **[OPEN]** |

### Transcript dataset schema
```
symbol             str    ticker, e.g. "AAPL"
company_name       str
company_id         float  Capital IQ id
year               int    fiscal year
quarter            int    fiscal quarter 1–4
date               str    "YYYY-MM-DD HH:MM:SS"  (call date AND time)
content            str    full raw transcript
structured_content list[{speaker, text}]   speaker-by-speaker segments
```
```python
from datasets import load_dataset
ds = load_dataset("kurry/sp500_earnings_transcripts")["train"]
```

**Study window:** event calls from **2015 to 2025**, subject to data availability and the agreed chronological split below. Earlier calls may be needed to construct each company's call history.

---

## 3. Target / label

Compare the company's adjusted close-to-close return with the equal-weight S&P
500 benchmark (`RSP`) over the same event interval:

```text
stock return = stock adjusted close on event day
               / stock adjusted close on previous trading day - 1
relative return = stock return - RSP return
```

Label the event `UP` when the relative return is zero or positive and `DOWN`
when it is negative. A tie counts as `UP`.

### 3.1 Event trading day and call timing

Treat transcript timestamps as Eastern Time. Use the actual XNYS exchange
calendar, including holidays and early closes:

- A call before the session open maps to that same session.
- A call at or after the session open and before the actual session close is
  excluded.
- A call at or after the actual session close maps to the next session.
- A call on a weekend or market holiday maps to the next session.

This means a call exactly at 09:30 ET is excluded on a regular trading day, and
a call exactly at the session close maps to the next session.

Some transcript timestamps are not real call times: calls stamped between
21:00 and 05:59 ET, or on a weekend or market holiday (often a publication
date). For these, use the nearest yfinance earnings release time for the same
ticker within 7 days, then apply the rules above. If no release time is found,
exclude the event as `suspicious_call_timestamp`.

### 3.2 Binary target

- `UP` if the relative return is zero or positive; `DOWN` if it is negative.
- Use adjusted stock and RSP close prices for the event session and immediately
  preceding exchange session.
- Keep both prices, both returns, and their difference in the label audit data.

---

## 4. Preprocessing

1. Remove empty or very short transcripts (some `content` values have length 0). Remove duplicates on (symbol, date).
2. Ticker cleanup for yfinance: e.g. `BRK.B → BRK-B`, `BF.B → BF-B`, renamed tickers (`FB → META`, etc.). Record which tickers fail to download. Survivorship bias is a **known limitation**, since delisted companies are often missing from yfinance.
   Snapshot-specific findings and exclusions are recorded in [`DATA_INVENTORY.md`](DATA_INVENTORY.md).
3. **Split each call into 3 sections** using `structured_content`:
   - **Prepared remarks:** management segments before the Q&A starts
   - **Analyst questions:** analyst segments during the Q&A
   - **Management answers:** management segments during the Q&A
   - Drop operator segments (the operator usually announces the start of the Q&A, which is a good split marker)
   - **[OPEN] This is the hardest heuristic.** Possible signals: the operator says something like "question-and-answer session" or "first question comes from…"; speaker names that match the analysts the operator introduced; names that show up in the prepared remarks are management. Build it, validate it by hand on about 20 calls, and log how many calls fail to split (drop or flag them).

---

## 5. Features (input to the models)

### 5.1 FinBERT sentiment features

- Split each earnings call into prepared remarks, analyst questions, and management answers (§4).
- Split section text into sentence-preserving chunks of **about 128 tokens**, as described in the pitch deck.
- Run frozen `ProsusAI/finbert` on each chunk to obtain positive, negative, and neutral probabilities.
- The deck specifies **five sentiment values per section**, or 15 sentiment inputs per call, plus EPS as the 16th input. It also mentions average and worst-chunk sentiment. **[OPEN]** Define the exact five values and how chunk scores are aggregated before implementation.
- **[VERIFY]** Confirm FinBERT's output label order using `model.config.id2label`.
- Cache per-chunk results to disk (for example, Parquet); this is an expensive step and should be reproducible.

### 5.2 Earnings surprise and call-to-call change

- Include EPS as the 16th current-call input, as specified in the deck. The source is yfinance earnings history (`EPS Estimate`, `Reported EPS`, `Surprise(%)`).
- Use yfinance `Surprise(%)`, capped at ±100%. When EPS is missing, set the surprise to 0 (met expectations) and record that it was filled.
- The project tests whether a change in tone adds information. The deck's FFN-B adds one input for the change in management tone versus the previous call. **[OPEN]** Define which feature represents management tone for this input.

### 5.3 Sequence construction

- Each call is represented by the same 16 inputs.
- The GRU uses the company's last four calls in chronological order: an input of shape `(4, 16)`.
- **[OPEN]** Decide how to handle events without four prior calls (drop them or pad/mask).
- Any learned preprocessing, such as scaling, must be fitted on training data only.

### 5.4 Loughran–McDonald dictionary

The pitch deck includes Loughran–McDonald word lists as a sentiment resource. **[OPEN]** Confirm its role and features in the planned model/baseline comparison before adding it to the pipeline.

---

## 6. Train / validation / test split (by date, never random)

| Split | Event dates |
|---|---|
| Train | 2015 – 2022 |
| Validation | 2023 (model selection and tuning) |
| Test | 2024 – 2025 (final evaluation; do not use for model selection) |

These calendar ranges come from the current pitch deck and replace the earlier split in this handoff. Split by event date, never randomly. No feature or sequence may use information from after its event date. Fit learned preprocessing using training data only.

---

## 7. Models: this ladder is the experiment

The reviewer's key point: to claim the GRU's gain comes from **sequential** information, the GRU has to beat a non-sequential model that already gets explicit change features.

| # | Model | Input |
|---|---|---|
| B0 | Random prediction | Expected accuracy: 50% |
| B1 | EPS rule | Beat → UP; miss → DOWN |
| B2 | Tone-change rule | Tone rose vs. the previous call → UP |
| B3 | Logistic regression | Same 16 current-call inputs |
| **A** | Feedforward network | Current call (16 inputs) |
| **B** | Feedforward network | A plus one explicit management-tone-change input (17 inputs) |
| **C** | **GRU** | Last four calls in order (4 × 16 inputs) |

How to read the results:
- B > A → the explicit tone-change input helps
- **C > B → the sequence carries information beyond the single explicit tone-change input.**
- C ≈ B → the explicit change may capture most of the useful signal; report this honestly.

Keep comparisons fair: use the same eligible events and splits, and document model configurations and tuning choices.

**[OPEN]** Choose architecture details and a tuning/early-stopping procedure using the validation set. Do not tune against the test set.

### Ablations

Any additional ablations are **[OPEN]** and should be scoped after the core deck comparisons are working.

---

## 8. Evaluation

- Primary metric: **directional accuracy** on the 2024–2025 test set.
- Compare all models on the same held-out test examples.
- The deck's success criterion is to outperform the baseline models on unseen data. **[OPEN]** Define which comparisons constitute success and whether secondary metrics or uncertainty estimates are required.
- Report class balance and per-model test accuracy so results can be interpreted in context.

---

## 9. Project sanity checks

1. **Feature check:** inspect chunk scores and section aggregates on a small sample to catch parsing, tokenization, and label-order mistakes.
2. **Label check:** inspect event dates and stock-minus-RSP return differences for a hand-checked sample; report UP/DOWN balance and the number of examples lost at each filtering step.
3. **Comparison check:** confirm all baseline and neural models use the same event dates and chronological split.

---

## 10. Reviewer feedback this design addresses (keep these traceable)

1. The prediction target comes from the stock's return relative to RSP; FinBERT supplies text features, not labels.
2. Inputs are per-section FinBERT sentiment summaries plus EPS. The exact per-section feature aggregation remains **[OPEN]** (§5.1).
3. The model comparison tests current-call inputs, an explicit management-tone-change input, and a four-call GRU sequence (§7).

---

## 11. Suggested repo layout
```
data/raw/            # HF parquet, price CSVs (gitignored)
data/interim/        # sections.parquet, finbert_chunks.parquet, labels.parquet
data/processed/      # features.parquet, windows_{train,val,test}.npz
src/
  load_transcripts.py
  prices.py          # yfinance download + caching, ticker mapping
  labels.py          # event-day logic and stock-versus-RSP return labels
  sections.py        # prepared remarks / analyst Q / mgmt A split
  finbert_features.py
  lm_features.py
  windows.py
  models.py          # MLP, GRU
  train.py / evaluate.py
notebooks/           # EDA, sanity checks, figures
config.yaml          # thresholds, windows, dates, seeds
```
Set random seeds, cache every expensive step, and log the counts at each filter step.

---

## 12. Literature (for the comments and report)
- Price, Doran, Peterson & Bliss (2012). Earnings conference calls and stock returns: the incremental informativeness of textual tone. *Journal of Banking & Finance* 36. (Dictionary tone in the Q&A predicts returns, but each call is scored on its own)
- Loughran & McDonald (2011). When is a liability not a liability? *Journal of Finance*. (Finance-specific dictionary)
- Ebrahim (2019). LSTM on earnings calls, Stanford CS230. (About 50% accuracy, single calls, raw text)
- Matsumoto, Pronk & Roelofsen (2011), *The Accounting Review*. (The Q&A section is more informative)
- Cohen, Malloy & Nguyen (2020). Lazy Prices, *Journal of Finance*. (Changes in company text matter)
- Kogan et al. (2009); Qin & Yang (2019). (Text predicts volatility)
- Araci (2019). FinBERT.