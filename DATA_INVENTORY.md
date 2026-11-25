# Data Inventory

This file records findings and exclusions for the current raw-data snapshot.
Raw and generated datasets remain in Git-ignored `data/` directories.

## Inspection

Run from the project root:

```sh
python scripts/inspect_raw_data.py
```

### Transcripts

- Path: `data/raw/transcripts/transcripts_raw.parquet`
- Rows: 33,362
- Unique symbols: 685
- Date range: 2005-10-13 14:45:00 through 2025-05-15 16:30:00
- Missing symbols: 0
- Invalid timestamps: 0
- Duplicate `(symbol, date)` rows beyond the first: 0
- Blank transcripts: 1

### Adjusted prices

- Path: `data/raw/prices/prices_yfinance_adjusted.parquet`
- Rows: 2,891
- Date range: 2013-12-02 through 2025-05-30
- Ticker columns: 686
- `RSP` is present.
- Every transcript symbol has a price-file column.
- 92 ticker columns had no close-price data in the original snapshot; 91 in the 2026-11-25 rebuild, which recovered `SHW`.

## Event labels

Run from the project root (see `README.md` for the full order):

```sh
python scripts/download_eps.py
python scripts/prepare_event_labels.py
python scripts/validate_event_labels.py
```

The validation script successfully checked all 21,135 candidate events.

These counts come from a rebuild of the raw data on 2026-11-25. That price
download recovered `SHW`, and Yahoo returned negative prices for one `PARA`
event, which `nonpositive_price` excluded.

### Timestamp corrections

Some transcript timestamps are not real call times. For example, `ABT` calls
are stamped around 23:00 while Yahoo dates the release 07:00 the next morning,
and weekend timestamps are usually publication dates after a weekday call.
Calls stamped 21:00–05:59 ET or on a non-trading day use the nearest Yahoo
earnings release time for the same ticker within 7 days instead.

| Call time source | Candidate events |
| --- | ---: |
| Transcript timestamp | 20,302 |
| Yahoo earnings release time | 651 |
| None found (excluded or already excluded) | 182 |

Of the 651 corrected events, 598 are eligible.

### Final counts

| Result | Count |
| --- | ---: |
| Candidate events from 2015 through 2025 | 21,135 |
| Eligible events | 12,539 |
| Excluded events | 8,596 |
| Eligible `UP` labels | 6,357 |
| Eligible `DOWN` labels | 6,182 |

| Split | Eligible | `UP` | `DOWN` |
| --- | ---: | ---: | ---: |
| Train, 2015–2022 | 9,261 | 4,699 | 4,562 |
| Validation, 2023 | 1,258 | 645 | 613 |
| Test, 2024–2025 | 2,020 | 1,013 | 1,007 |

## Exclusions

Each excluded event has one primary reason, checked in the order listed in
`prepare_event_labels.py`. `missing_stock_price_history` takes priority over
timing reasons, so these counts should not be read as independent timing
totals.

| Reason | Events | Meaning |
| --- | ---: | --- |
| `during_market_hours` | 6,673 | The call began at or after the session open and before the actual session close. |
| `missing_stock_price_history` | 1,786 | The ticker has no close-price data anywhere in the raw price snapshot (list below). Its events are excluded without retrying or remapping the ticker. |
| `missing_stock_previous_close` | 98 | A partially covered ticker lacks prices for the required event interval. All 98 events lack both the previous-session and event-session closes. Renaming this reason to `missing_stock_prices_for_event_interval` is deferred. |
| `suspicious_call_timestamp` | 37 | The transcript time is implausible and no Yahoo release time was found within 7 days. |
| `blank_transcript` | 1 | The transcript content is null, empty, or whitespace-only. |
| `nonpositive_price` | 1 | At least one required stock or RSP close is zero or negative. |
| `missing_stock_event_close` | 0 | The stock has a previous-session close but no event-session close. |
| `missing_rsp_previous_close` | 0 | RSP has no close for the previous trading session. |
| `missing_rsp_event_close` | 0 | RSP has no close for the event trading session. |

### Tickers without close-price data

`ABMD`, `ADS`, `AKS`, `ALTR`, `ALXN`, `AMBC`, `ANSS`, `AT`, `ATGE`,
`ATVI`, `AVB`, `BBBY`, `BF.B`, `BIG`, `BK`, `CBH`, `CERN`, `CHIR`, `CIT`,
`CMA`, `COOP`, `CTLT`, `CTRA`, `CXO`, `DAY`, `DFS`, `DISCK`, `DISH`, `DNB`,
`DO`, `DRE`, `EA`, `ENDP`, `EQR`, `ETFC`, `FI`, `FL`, `FLIR`, `FRC`, `HBI`,
`HES`, `HFC`, `HOLX`, `IAC`, `IGT`, `IPG`, `JNPR`, `JWN`, `K`, `KSU`,
`KVUE`, `LEG`, `LIFE`, `LM`, `LSI`, `MDP`, `MMC`, `MNK`, `MRO`, `MXIM`,
`NBL`, `NLSN`, `ODP`, `PBCT`, `PDCO`, `PLL`, `POM`, `PXD`, `QEP`, `QRVO`,
`RRD`, `SAF`, `SEE`, `SIVB`, `SNV`, `SRCL`, `TGNA`, `TIF`, `TSS`,
`TWTR`, `VAR`, `VIAB`, `WBA`, `WBD`, `WCG`, `WPX`, `WRK`, `WYND`, `X`,
`XEC`, `XLNX`

## EPS coverage

```sh
python scripts/download_eps.py
python scripts/match_eps_to_events.py
```

- Tickers requested: all 685 transcript tickers. 634 returned EPS rows
  (54,872 rows); 51 returned none, almost all delisted.
- `limit=100` reaches back to the early 2000s, covering the 2015–2025 study window.
- Match rule: same ticker, EPS date on the call date (after any timestamp
  correction) or up to 3 days before it. EPS dated after the call is never used.

| Match status | Eligible events | Meaning |
| --- | ---: | --- |
| `matched` | 12,305 | One EPS row falls inside the window. |
| `no_eps_row_near_call` | 232 | The ticker has EPS history, but no row falls inside the window. |
| `ambiguous_eps_match` | 2 | Two different rows share the closest date; neither is used. |

| Split | Share with estimate | Share with reported EPS | Share with surprise |
| --- | ---: | ---: | ---: |
| Train, 2015–2022 | 97.6% | 97.7% | 97.7% |
| Validation, 2023 | 98.9% | 98.9% | 98.9% |
| Test, 2024–2025 | 99.1% | 99.1% | 99.0% |

Yearly surprise coverage ranges from 96.6% (2015, 2019) to 99.2% (2025).

### EPS model input

`eps_surprise_feature` is yfinance `Surprise(%)` capped at ±100%, with missing
values set to 0 (met expectations). `eps_surprise_missing` records which events
were filled.

- Surprise values capped: 368 (median surprise is +4.9%; the 1st and 99th
  percentiles are −88% and +221%).
- Missing surprise set to 0: 250 eligible events (2.0%).

## Known limitation

Excluding companies without price history may introduce survivorship bias. The
number of excluded events must be reported alongside model results.

Ticker symbols can also be renamed or reused by unrelated companies. Matching a
transcript and price series by ticker and date alone does not prove that they
belong to the same company. Requiring prices on the event date and previous
trading date prevents many bad matches, but it cannot detect every case of
ticker reuse. Suspicious ticker histories should be checked manually, and this
identity limitation should be reported with the results.
