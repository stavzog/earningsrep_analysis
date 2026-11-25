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
- 92 ticker columns have no close-price data.

## Event labels

Run from the project root:

```sh
python scripts/prepare_event_labels.py
python scripts/validate_event_labels.py
```

The validation script successfully checked all 21,135 candidate events.

### Final counts

| Result | Count |
| --- | ---: |
| Candidate events from 2015 through 2025 | 21,135 |
| Eligible events | 12,577 |
| Excluded events | 8,558 |
| Eligible `UP` labels | 6,366 |
| Eligible `DOWN` labels | 6,211 |

| Split | Eligible | `UP` | `DOWN` |
| --- | ---: | ---: | ---: |
| Train, 2015–2022 | 9,293 | 4,706 | 4,587 |
| Validation, 2023 | 1,262 | 647 | 615 |
| Test, 2024–2025 | 2,022 | 1,013 | 1,009 |

## Exclusions

Each excluded event has one primary reason. `missing_stock_price_history` takes
priority over `during_market_hours` when both apply, so these counts should not
be read as independent timing totals.

| Reason | Events | Meaning |
| --- | ---: | --- |
| `during_market_hours` | 6,632 | The call began at or after the session open and before the actual session close. |
| `missing_stock_price_history` | 1,827 | The ticker is one of the 92 columns with no close-price data anywhere in the raw price snapshot. Its events are excluded without retrying or remapping the ticker. |
| `missing_stock_previous_close` | 98 | A partially covered ticker lacks prices for the required event interval. In the current output, all 98 events lack both the previous-session and event-session closes. Renaming this reason to `missing_stock_prices_for_event_interval` is deferred. |
| `blank_transcript` | 1 | The transcript content is null, empty, or whitespace-only. |
| `missing_stock_event_close` | 0 | The stock has a previous-session close but no event-session close. |
| `missing_rsp_previous_close` | 0 | RSP has no close for the previous trading session. |
| `missing_rsp_event_close` | 0 | RSP has no close for the event trading session. |
| `nonpositive_price` | 0 | At least one required stock or RSP close is zero or negative. |

### Tickers without close-price data

`ABMD`, `ADS`, `AKS`, `ALTR`, `ALXN`, `AMBC`, `ANSS`, `AT`, `ATGE`,
`ATVI`, `AVB`, `BBBY`, `BF.B`, `BIG`, `BK`, `CBH`, `CERN`, `CHIR`, `CIT`,
`CMA`, `COOP`, `CTLT`, `CTRA`, `CXO`, `DAY`, `DFS`, `DISCK`, `DISH`, `DNB`,
`DO`, `DRE`, `EA`, `ENDP`, `EQR`, `ETFC`, `FI`, `FL`, `FLIR`, `FRC`, `HBI`,
`HES`, `HFC`, `HOLX`, `IAC`, `IGT`, `IPG`, `JNPR`, `JWN`, `K`, `KSU`,
`KVUE`, `LEG`, `LIFE`, `LM`, `LSI`, `MDP`, `MMC`, `MNK`, `MRO`, `MXIM`,
`NBL`, `NLSN`, `ODP`, `PBCT`, `PDCO`, `PLL`, `POM`, `PXD`, `QEP`, `QRVO`,
`RRD`, `SAF`, `SEE`, `SHW`, `SIVB`, `SNV`, `SRCL`, `TGNA`, `TIF`, `TSS`,
`TWTR`, `VAR`, `VIAB`, `WBA`, `WBD`, `WCG`, `WPX`, `WRK`, `WYND`, `X`,
`XEC`, `XLNX`

## EPS coverage

Run from the project root after preparing event labels:

```sh
python scripts/download_eps.py
python scripts/match_eps_to_events.py
```

These counts come from a rebuild of the raw data on 2026-11-25. That price
download recovered `SHW` (2 more eligible events), and Yahoo returned negative
prices for one `PARA` event, which `nonpositive_price` excluded. The rebuild
has 12,578 eligible events instead of 12,577.

- Tickers requested: 523. All returned EPS rows (46,069 rows in total).
- `limit=100` reaches back to the early 2000s, covering the 2015–2025 study window.
- Match rule: same ticker, EPS date on the call date or up to 3 days before it.
  EPS dated after the call is never used.

| Match status | Events | Meaning |
| --- | ---: | --- |
| `matched` | 12,162 | One EPS row falls inside the window. |
| `no_eps_row_near_call` | 414 | The ticker has EPS history, but no row falls inside the window. |
| `ambiguous_eps_match` | 2 | Two different rows share the closest date; neither is used. |
| `no_eps_history_for_ticker` | 0 | yfinance returned no EPS rows for the ticker. |

| Split | Share with estimate | Share with reported EPS | Share with surprise |
| --- | ---: | ---: | ---: |
| Train, 2015–2022 | 96.0% | 96.0% | 96.0% |
| Validation, 2023 | 97.7% | 97.7% | 97.7% |
| Test, 2024–2025 | 98.6% | 98.6% | 98.5% |

Yearly coverage ranges from 94.7% (2016) to 99.2% (2025).

### Timestamp findings from unmatched events

- 105 unmatched events have an EPS row dated the day after the call, mostly
  `ROST`, `ABT`, and `ADI`. Their transcript times look shifted; for example,
  an `ABT` call is timestamped 22:45 while Yahoo dates the release 07:00 the
  next morning.
- About 50 unmatched events have an EPS row 4 days earlier; these calls carry
  weekend timestamps, which suggests a publication date rather than the call
  date.

Both patterns could also affect event-day assignment in the labels and should
be reviewed before the matching window or label timing is changed.

## Known limitation

Excluding companies without price history may introduce survivorship bias. The
number of excluded events must be reported alongside model results.

Ticker symbols can also be renamed or reused by unrelated companies. Matching a
transcript and price series by ticker and date alone does not prove that they
belong to the same company. Requiring prices on the event date and previous
trading date prevents many bad matches, but it cannot detect every case of
ticker reuse. Suspicious ticker histories should be checked manually, and this
identity limitation should be reported with the results.
