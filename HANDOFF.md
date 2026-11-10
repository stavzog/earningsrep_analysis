# Project Handoff: Earnings Call Language → Stock Reaction (FinBERT + GRU)

Context for the coding agent. This is a university ML class project. Everything below has been decided with the team and the course reviewers unless it's marked **[OPEN]** or **[VERIFY]**.

---

## 1. Research question

**Do markets react to what management says, or to how it differs from what they usually say?**

Formal objective: predict a stock's next-day **abnormal return** (UP/DOWN) from the language of its earnings call. Then test whether information about **how the call changed compared with the company's past calls**, and specifically the **sequence of calls read by a GRU**, predicts better than looking at the current call alone.

Expected outcome: direction is hard to predict because markets are efficient. Published work gets roughly 50–55% accuracy, and Ebrahim (2019, Stanford CS230, LSTM) got about 50%. A modest result is acceptable. What matters is a **clean, fair comparison** between the models and baselines (§7).

---

## 2. Data sources

| Data | Source | Notes |
|---|---|---|
| Earnings call transcripts | Hugging Face `kurry/sp500_earnings_transcripts` | 33,362 rows, 685 companies, 2005-10 to 2025-05, Parquet, ~1.8 GB, single `train` split |
| Daily stock prices | `yfinance` | Use adjusted prices (`auto_adjust=True`) so splits and dividends don't create fake returns |
| Market benchmark | `yfinance` ticker `^GSPC` (S&P 500) | Used for the abnormal return |
| Sector benchmarks (robustness) | `yfinance` SPDR sector ETFs: XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLB, XLRE, XLC | XLRE starts in 2015 and XLC in 2018; fall back to ^GSPC before those dates |
| EPS actual vs. estimate | `yfinance` `Ticker.get_earnings_dates(limit=...)` → `EPS Estimate`, `Reported EPS`, `Surprise(%)` | **[VERIFY]** how far back coverage goes per ticker; report the share of missing values |
| Sentiment model | Hugging Face `ProsusAI/finbert` | Pre-trained, frozen. Gives positive/negative/neutral probabilities and 768-d hidden states |
| Keyword dictionary (baseline only) | Loughran–McDonald Master Dictionary (Notre Dame SRAF) | Positive / Negative / Uncertainty word lists |

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

**Study window:** calls from **2015 to 2024** (about 20,200 calls). Earlier years are needed only to build the history (past calls, estimation windows).

---

## 3. Target / label (most important section)

The team asked for "stock move minus S&P 500 on the day, or the standard way to do this." The standard approach in finance is an **event study with a market-model abnormal return** (MacKinlay 1997). The simple "stock minus S&P 500" version is the market-adjusted special case of that model (it fixes α = 0 and β = 1). Implement **both**: the market model as the main label and market-adjusted as a robustness check.

### 3.1 Event day (day 0): watch the timing
Day 0 is the **first trading day whose close reflects the call**:
- Call **before 09:30 ET** → day 0 = same trading day
- Call **during market hours (09:30–16:00 ET)** → day 0 = same trading day (flag these; they're rare)
- Call **after 16:00 ET** (most calls, e.g. 16:30) → day 0 = **next** trading day
- Weekends and holidays → the next trading day in the price index

**[VERIFY]** the timezone of the `date` field. Examples show 16:30:00, which suggests US Eastern time, but confirm this by spot-checking a few well-known calls (e.g. AAPL is always after the close). If the time is missing or 00:00:00, use a conservative fallback (e.g. treat it as after the close) and add an `time_imputed` flag.

### 3.2 Main label: market-model abnormal return
For stock *i*, using daily simple returns:

1. **Estimation window:** trading days **[-250, -11]** relative to day 0. Require at least **120** valid observations, otherwise drop the event. The window must **not overlap** the event.
2. Fit by OLS: `R_i,t = α_i + β_i · R_m,t + ε_i,t`, where `R_m` is the ^GSPC return.
3. Abnormal return on day 0: `AR_i,0 = R_i,0 − (α̂_i + β̂_i · R_m,0)`
4. Residual standard deviation from the estimation window: `σ̂_i = std(ε_i,t)`, using L − 2 degrees of freedom
5. **Standardized abnormal return:** `SAR_i,0 = AR_i,0 / σ̂_i`

**Why use SAR:** it adjusts for the volatility regime. A 3% move in March 2020 is ordinary, while in a calm year it's large. A reviewer explicitly asked us to normalize for global trends and COVID. Subtracting the market handles market-wide moves, and dividing by σ̂ handles volatility.

### 3.3 Binary label
- `UP` if `SAR > +0.5`, `DOWN` if `SAR < −0.5`, otherwise **drop the event** (it's too close to zero to be a meaningful label)
- Make the threshold configurable. Also report results with the threshold at 0 (keeping all events)
- Store the continuous `AR`, `SAR` and `CAR[0,+1]` values too, for the secondary analyses

### 3.4 Robustness labels (calculate and store them all)
- `AR_mktadj = R_i,0 − R_m,0` (the simple "stock minus S&P 500" version)
- `CAR[0,+1]` (sum of market-model ARs on days 0 and +1)
- **Sector-adjusted:** the same market model but with the company's sector ETF as `R_m` (sector from `yf.Ticker(t).info["sector"]` or a static GICS map)
- **Secondary target [OPTIONAL]:** magnitude, `|SAR|`, i.e. a big vs. small move. There's evidence that language predicts how much a stock moves better than which way (Kogan et al. 2009; Qin & Yang 2019)

---

## 4. Preprocessing

1. Remove empty or very short transcripts (some `content` values have length 0). Remove duplicates on (symbol, date).
2. Ticker cleanup for yfinance: e.g. `BRK.B → BRK-B`, `BF.B → BF-B`, renamed tickers (`FB → META`, etc.). Record which tickers fail to download. Survivorship bias is a **known limitation**, since delisted companies are often missing from yfinance.
3. **Split each call into 3 sections** using `structured_content`:
   - **Prepared remarks:** management segments before the Q&A starts
   - **Analyst questions:** analyst segments during the Q&A
   - **Management answers:** management segments during the Q&A
   - Drop operator segments (the operator usually announces the start of the Q&A, which is a good split marker)
   - **[OPEN] This is the hardest heuristic.** Possible signals: the operator says something like "question-and-answer session" or "first question comes from…"; speaker names that match the analysts the operator introduced; names that show up in the prepared remarks are management. Build it, validate it by hand on about 20 calls, and log how many calls fail to split (drop or flag them).

---

## 5. Features (input to the models)

### 5.1 FinBERT sentiment per section
- Tokenize each section and split it into chunks of **≤512 tokens** (use a small stride/overlap, or none, but keep it consistent)
- Run `ProsusAI/finbert` on each chunk → softmax probabilities `[positive, negative, neutral]`
  - **[VERIFY]** the label order using `model.config.id2label`
- Aggregate per section:
  - `mean_pos`, `mean_neg`, `mean_neu`
  - `frac_neg_chunks` (share of chunks where negative is the top class)
  - `net = mean_pos − mean_neg`
- That gives 3 sections × 5 features = **15 features per call**
- Cache the per-chunk results to disk (Parquet). FinBERT over about 20k long transcripts is the most expensive step; batch it on GPU.

### 5.2 Change features (the core idea)
For each of the 15 features:
- `Δ_last = x_t − x_{t−1}` (change from the company's previous call)
- `Δ_avg4 = x_t − mean(x_{t−4..t−1})` (change from the company's average over its last 4 calls)
- **Cross-sectional normalization [recommended]:** also subtract the mean of that feature across **all companies' calls in the previous ~90 days** (use only calls **before** the current event date, to avoid look-ahead). This removes periods when everyone sounded negative, like 2020.

### 5.3 Earnings surprise
- `eps_surprise_pct` from yfinance, plus `beat = 1 if Reported EPS > Estimate`
- Add a `eps_missing` flag. Don't silently drop events with missing EPS; test both ways

### 5.4 Compressed embedding [OPTIONAL, ablation only]
- Mean-pooled FinBERT hidden states for each section (768-d) → **PCA to ~32 dimensions, fitted on the training set only**
- Use it only in the ablation. The reviewers warned that the raw 768-d embedding is too noisy on its own, and it mostly encodes topic/industry rather than tone

### 5.5 Loughran–McDonald (baseline only, NOT a GRU input)
Per section: `%pos`, `%neg`, `%uncertainty` (count / total words), `net_tone = (P − N)/(P + N)`, plus the same Δ features. Use these only for the logistic regression baseline and the sanity check.

### 5.6 Sequence construction
- One feature vector per call: FinBERT (15) + Δ features + EPS (+ optional PCA)
- For each event, take the company's **last 4 calls including the current one**, in time order → tensor `(4, n_features)`
- Require 4 consecutive calls (or use padding + mask; **[OPEN]** pick one and document it)
- All companies' windows are stacked into one dataset: `X: (N, 4, F)`, `y: (N,)`. A window always contains a **single company**. One shared GRU learns from all of them.
- Standardize features with a scaler **fitted on the training set only**

---

## 6. Train / validation / test split (by date, never random)

| Split | Event dates |
|---|---|
| Train | 2015 – 2021 |
| Validation | 2022 (tuning, early stopping, threshold selection) |
| Test | 2023 – 2024 (touch once, at the end) |

Shuffling is fine **within** the training set. No window in train/validation may contain information from after its own event date. Rolling averages, PCA, scalers and the cross-sectional means must all use only past or training data.

---

## 7. Models: this ladder is the experiment

The reviewer's key point: to claim the GRU's gain comes from **sequential** information, the GRU has to beat a non-sequential model that already gets explicit change features.

| # | Model | Input |
|---|---|---|
| B0 | Majority class | — |
| B1 | EPS rule | beat → UP, miss → DOWN |
| B2 | Logistic regression | Loughran–McDonald tone features (+ Δ) |
| B3 | Logistic regression | FinBERT features of the current call + EPS |
| **A** | MLP | FinBERT features of the **current call** + EPS |
| **B** | MLP | A + **explicit change features** (Δ_last, Δ_avg4) |
| **C** | **GRU** | Same per-call features for the **last 4 calls** as a sequence |

How to read the results:
- B > A → comparing with past calls helps
- **C > B → the sequence carries information beyond a simple change.** This is the result that justifies the GRU.
- C ≈ B → the signal is just "this call vs. the previous call" (still a valid finding)

Keep B and C comparable: same features, same splits, a similar number of parameters, and the same tuning budget.

Suggested GRU: 1 layer, hidden size 32–64, dropout 0.2–0.5, last hidden state → dense → sigmoid. BCE loss, Adam, early stopping on validation AUC. These are small models on purpose, since the data is noisy.

### Ablations (run on the GRU and the MLPs)
FinBERT only → + Δ features → + cross-sectional normalization → + EPS → + PCA embedding.
Optionally, section importance: drop one section at a time (prepared remarks / analyst questions / management answers). Price et al. (2012) found the Q&A tone carries the most signal.

---

## 8. Evaluation

- Metrics: **AUC (primary)**, accuracy, F1, and class balance on the test set
- Significance: bootstrap confidence intervals for the AUC difference between C and B and between C and B1 (or a DeLong test)
- Success criterion (set in advance): the GRU beats **both** the EPS rule (B1) and MLP+change (B) on test AUC, with a confidence interval that excludes zero
- **Robustness:** rerun the main comparison (i) excluding 2020, (ii) with the sector-adjusted label, (iii) with `CAR[0,+1]`, (iv) with the market-adjusted label, (v) with SAR threshold 0
- Optional: the same ladder with the magnitude target `|SAR|`

---

## 9. Sanity checks (the reviewers asked about these)

1. **Is the sentiment meaningful?** Correlate FinBERT `net` with Loughran–McDonald `net_tone` per section. Optionally, hand-label 50–100 Q&A passages as positive/negative and report how well each tool agrees with the hand labels.
2. **Is there any signal before the GRU?** Group events into quintiles by `Δ_avg4` of management-answers tone and plot the mean SAR per quintile. If the pattern is flat, say so honestly.
3. **Label check:** distribution of AR/SAR, share of UP/DOWN after the threshold, and the number of events lost at each filtering step (build a funnel table for the report).

---

## 10. Reviewer feedback this design addresses (keep these traceable)

1. "There's no sentiment label, so you're trusting the embedding." → The label comes from prices. FinBERT gives features. Sanity check 9.1.
2. "How does Loughran–McDonald map a call to a sentiment?" → Continuous normalized counts and net tone (not a majority vote), used as a baseline.
3. "What exactly is your input? A raw embedding with UP/DOWN as-is may not be enough." → Explicit per-section sentiment + change features + EPS (§5); the raw embedding is only an optional ablation.
4. "Normalize the target for global trends / COVID." → Market-model AR, standardized by the stock's volatility (SAR), sector-adjusted robustness check, cross-sectional feature normalization, and a robustness run without 2020.
5. "Give the fully connected network an explicit change variable so any GRU gain is truly sequential." → Model B in §7.

---

## 11. Suggested repo layout
```
data/raw/            # HF parquet, price CSVs (gitignored)
data/interim/        # sections.parquet, finbert_chunks.parquet, labels.parquet
data/processed/      # features.parquet, windows_{train,val,test}.npz
src/
  load_transcripts.py
  prices.py          # yfinance download + caching, ticker mapping
  labels.py          # event day logic, market model, AR/SAR/CAR, sector variant
  sections.py        # prepared remarks / analyst Q / mgmt A split
  finbert_features.py
  lm_features.py
  change_features.py
  windows.py
  models.py          # MLP, GRU
  train.py / evaluate.py
notebooks/           # EDA, sanity checks, figures
config.yaml          # thresholds, windows, dates, seeds
```
Set random seeds, cache every expensive step, and log the counts at each filter step.

---

## 12. Literature (for the comments and report)
- MacKinlay, A. C. (1997). Event studies in economics and finance. *Journal of Economic Literature*. (Market-model abnormal returns, estimation and event windows)
- Price, Doran, Peterson & Bliss (2012). Earnings conference calls and stock returns: the incremental informativeness of textual tone. *Journal of Banking & Finance* 36. (Dictionary tone in the Q&A predicts returns, but each call is scored on its own)
- Loughran & McDonald (2011). When is a liability not a liability? *Journal of Finance*. (Finance-specific dictionary)
- Ebrahim (2019). LSTM on earnings calls, Stanford CS230. (About 50% accuracy, single calls, raw text)
- Matsumoto, Pronk & Roelofsen (2011), *The Accounting Review*. (The Q&A section is more informative)
- Cohen, Malloy & Nguyen (2020). Lazy Prices, *Journal of Finance*. (Changes in company text matter)
- Kogan et al. (2009); Qin & Yang (2019). (Text predicts volatility)
- Araci (2019). FinBERT.