"""Download yfinance EPS history for every transcript ticker."""

# Run after download_raw_data.py and before prepare_event_labels.py:
# python -m pip install pandas pyarrow yfinance lxml
# python scripts/download_eps.py

import time
from pathlib import Path

import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT_PATH = ROOT / "data/raw/transcripts/transcripts_raw.parquet"
EPS_PATH = ROOT / "data/raw/eps/eps_yfinance.parquet"
FAILED_PATH = ROOT / "data/raw/eps/eps_failed_tickers.csv"

# Number of past earnings dates to request per ticker (about 25 years).
LIMIT = 100
PAUSE_SECONDS = 0.5
ATTEMPTS = 3


def main():
    symbols = sorted(
        pd.read_parquet(TRANSCRIPT_PATH, columns=["symbol"])["symbol"].unique()
    )
    frames = []
    failures = []

    for number, symbol in enumerate(symbols, start=1):
        # yfinance writes share classes with a hyphen, e.g. BRK.B -> BRK-B.
        yf_symbol = symbol.replace(".", "-")
        print(f"[{number}/{len(symbols)}] {yf_symbol}")

        # Retry because Yahoo requests sometimes time out.
        for attempt in range(ATTEMPTS):
            try:
                dates = yf.Ticker(yf_symbol).get_earnings_dates(limit=LIMIT)
                break
            except Exception as error:
                dates = None
                last_error = str(error)
                time.sleep(5)
        else:
            failures.append({"symbol": symbol, "error": last_error})
            continue

        if dates is None or dates.empty:
            failures.append({"symbol": symbol, "error": "no rows returned"})
            continue

        dates = dates.reset_index()
        dates.insert(0, "symbol", symbol)
        frames.append(dates)
        time.sleep(PAUSE_SECONDS)

    if not frames:
        raise RuntimeError("yfinance returned no EPS data.")

    eps = pd.concat(frames, ignore_index=True)
    EPS_PATH.parent.mkdir(parents=True, exist_ok=True)
    eps.to_parquet(EPS_PATH, index=False)
    pd.DataFrame(failures, columns=["symbol", "error"]).to_csv(
        FAILED_PATH, index=False
    )

    print(f"\nTickers requested: {len(symbols)}")
    print(f"Tickers with EPS rows: {eps['symbol'].nunique()}")
    print(f"Tickers failed or empty: {len(failures)}")
    print(f"EPS rows: {len(eps):,}")
    print(f"Columns: {list(eps.columns)}")
    print(f"\nSaved EPS history to {EPS_PATH}")
    print(f"Saved failed tickers to {FAILED_PATH}")


if __name__ == "__main__":
    main()
