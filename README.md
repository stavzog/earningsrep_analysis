# Sentiment Analysis on Earnings Calls

We will be making a ANN model to predict whether a company's stock will go up or down based on earnings call data. Our main model will be a GRU that accepts 4-6 calls as input in order to learn the patterns in how tone changes. Then it predicts whether the stock price will increase or decrease.

## Download raw data

Install the loader dependencies and run the script from the project root:

```sh
python -m pip install datasets pandas yfinance pyarrow
python scripts/download_raw_data.py
```

The script saves transcripts and adjusted prices under the Git-ignored
`data/raw/` directory. It requests prices from 2013-12-01 up to (but not
including) 2025-06-01 and includes `RSP`; change the date constants in the
script if needed. It does not clean or label the data.

## Prepare and validate event labels

Install the exchange-calendar dependency, then run the preparation and
validation scripts from the project root:

```sh
python -m pip install exchange-calendars
python scripts/prepare_event_labels.py
python scripts/validate_event_labels.py
```

The preparation script writes a complete audit to
`data/interim/event_labels_audit.parquet` and eligible labels to
`data/processed/eligible_event_labels.parquet`. Both locations are Git-ignored.
The validation script checks calendar alignment, return calculations, labels,
and representative samples.

## Download and match EPS data

Run after preparing event labels:

```sh
python -m pip install yfinance lxml
python scripts/download_eps.py
python scripts/match_eps_to_events.py
```

`download_eps.py` saves yfinance earnings history to `data/raw/eps/`.
`match_eps_to_events.py` matches each eligible event to the EPS row dated on
the call date or up to 3 days before it, writes
`data/interim/event_eps.parquet`, and prints coverage by split and year.
Missing values are kept as nulls with an `eps_match_status` reason.
