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

## Exclusions

| Reason | Affected data | Handling |
| --- | ---: | --- |
| `missing_stock_price_history` | 92 tickers | Exclude their events without retrying or remapping the tickers. Record affected ticker and event counts in the label audit output. |
| `blank_transcript` | 1 transcript | Exclude the transcript and record the reason in the relevant audit output. |

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

## Known limitation

Excluding companies without price history may introduce survivorship bias. The
number of excluded events must be reported alongside model results.

Ticker symbols can also be renamed or reused by unrelated companies. Matching a
transcript and price series by ticker and date alone does not prove that they
belong to the same company. Requiring prices on the event date and previous
trading date prevents many bad matches, but it cannot detect every case of
ticker reuse. Suspicious ticker histories should be checked manually, and this
identity limitation should be reported with the results.
