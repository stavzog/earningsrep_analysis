"""Download the raw transcript and adjusted-price files to data/raw/."""

# run with
# python -m pip install datasets pandas yfinance pyarrow
# python scripts/download_raw_data.py


from pathlib import Path

import pandas as pd
import yfinance as yf
from datasets import load_dataset


ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT_PATH = ROOT / "data/raw/transcripts/transcripts_raw.parquet"
PRICE_PATH = ROOT / "data/raw/prices/prices_yfinance_adjusted.parquet"

# yfinance's end date is exclusive.
PRICE_START = "2013-12-01"
PRICE_END = "2025-06-01"


def main():
    TRANSCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PRICE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if TRANSCRIPT_PATH.exists():
        print(f"Transcripts already exist: {TRANSCRIPT_PATH}")
    else:
        print("Downloading transcripts from Hugging Face...")
        transcripts = load_dataset(
            "kurry/sp500_earnings_transcripts",
            split="train",
        )
        transcripts.to_parquet(TRANSCRIPT_PATH)
        print(f"Saved {len(transcripts):,} transcript rows to {TRANSCRIPT_PATH}")

    if PRICE_PATH.exists():
        print(f"Adjusted prices already exist: {PRICE_PATH}")
    else:
        symbols = pd.read_parquet(
            TRANSCRIPT_PATH,
            columns=["symbol"],
        )["symbol"].dropna().unique()
        tickers = sorted({str(symbol) for symbol in symbols} | {"RSP"})

        print(f"Downloading adjusted prices for {len(tickers)} tickers...")
        prices = yf.download(
            tickers=tickers,
            start=PRICE_START,
            end=PRICE_END,
            auto_adjust=True,
            progress=False,
        )
        if prices.empty:
            raise RuntimeError("yfinance returned no price data.")

        prices.to_parquet(PRICE_PATH)
        print(f"Saved {len(prices):,} price rows to {PRICE_PATH}")


if __name__ == "__main__":
    main()
