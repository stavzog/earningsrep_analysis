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

## Prepare labels and EPS features

Run from the project root after downloading the raw data:

```sh
python -m pip install exchange-calendars yfinance lxml
python scripts/download_eps.py
python scripts/prepare_event_labels.py
python scripts/validate_event_labels.py
python scripts/match_eps_to_events.py
```

- `download_eps.py` saves yfinance earnings history for every transcript
  ticker to `data/raw/eps/`. It runs first because the label script uses Yahoo
  earnings times to correct implausible transcript timestamps.
- `prepare_event_labels.py` writes a complete audit to
  `data/interim/event_labels_audit.parquet` and eligible labels to
  `data/processed/eligible_event_labels.parquet`.
- `validate_event_labels.py` checks calendar alignment, return calculations,
  labels, and representative samples.
- `match_eps_to_events.py` matches each eligible event to an EPS row and
  writes the capped surprise feature to `data/interim/event_eps.parquet`.

All outputs are Git-ignored.
