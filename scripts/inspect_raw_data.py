"""Print a small inventory of the downloaded raw datasets."""

from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT_PATH = ROOT / "data/raw/transcripts/transcripts_raw.parquet"
PRICE_PATH = ROOT / "data/raw/prices/prices_yfinance_adjusted.parquet"


def count_blank_transcripts(path):
    blank_count = 0
    parquet_file = pq.ParquetFile(path)

    for batch in parquet_file.iter_batches(columns=["content"], batch_size=256):
        content = batch.column(0).to_pylist()
        blank_count += sum(text is None or not text.strip() for text in content)

    return blank_count


def get_close_prices(prices):
    if not isinstance(prices.columns, pd.MultiIndex):
        if "Close" not in prices.columns:
            raise ValueError("The price file has no Close column.")
        return prices[["Close"]]

    for level in range(prices.columns.nlevels):
        if "Close" in prices.columns.get_level_values(level):
            return prices.xs("Close", axis="columns", level=level)

    raise ValueError("The price file has no Close column.")


def inspect_transcripts():
    parquet_file = pq.ParquetFile(TRANSCRIPT_PATH)
    transcripts = pd.read_parquet(
        TRANSCRIPT_PATH,
        columns=["symbol", "date"],
    )
    dates = pd.to_datetime(transcripts["date"], errors="coerce")

    print("TRANSCRIPTS")
    print(f"Path: {TRANSCRIPT_PATH}")
    print(f"Rows: {parquet_file.metadata.num_rows:,}")
    print(f"Columns: {parquet_file.schema_arrow.names}")
    print(f"Unique symbols: {transcripts['symbol'].nunique():,}")
    print(f"Missing symbols: {transcripts['symbol'].isna().sum():,}")
    print(f"Invalid timestamps: {dates.isna().sum():,}")
    print(f"First timestamp: {dates.min()}")
    print(f"Last timestamp: {dates.max()}")
    print(
        "Duplicate (symbol, date) rows beyond the first: "
        f"{transcripts.duplicated(['symbol', 'date']).sum():,}"
    )
    print(f"Blank transcripts: {count_blank_transcripts(TRANSCRIPT_PATH):,}")
    print("Calls by year:")
    print(dates.dt.year.value_counts().sort_index().to_string())


def inspect_prices():
    prices = pd.read_parquet(PRICE_PATH)
    closes = get_close_prices(prices)
    closes.columns = closes.columns.astype(str)

    transcript_symbols = set(
        pd.read_parquet(TRANSCRIPT_PATH, columns=["symbol"])["symbol"]
        .dropna()
        .astype(str)
    )
    price_symbols = set(closes.columns)
    missing_columns = sorted(transcript_symbols - price_symbols)
    no_close_data = sorted(
        symbol for symbol in closes.columns if closes[symbol].notna().sum() == 0
    )

    print("\nPRICES")
    print(f"Path: {PRICE_PATH}")
    print(f"Rows: {len(prices):,}")
    print(f"Index type: {type(prices.index).__name__}")
    print(f"First date: {prices.index.min()}")
    print(f"Last date: {prices.index.max()}")
    print(f"Column levels: {prices.columns.names}")
    print(f"Price fields: {sorted(set(prices.columns.get_level_values(0)))}")
    print(f"Ticker columns: {len(closes.columns):,}")
    print(f"RSP present: {'RSP' in price_symbols}")
    print(f"Transcript symbols absent from price columns: {len(missing_columns):,}")
    print(f"Absent symbols: {missing_columns}")
    print(f"Ticker columns with no close data: {len(no_close_data):,}")
    print(f"Tickers with no close data: {no_close_data}")

    dotted_symbols = sorted(symbol for symbol in transcript_symbols if "." in symbol)
    print("Dotted ticker check:")
    for symbol in dotted_symbols:
        normalized = symbol.replace(".", "-")
        print(
            f"  {symbol}: original={'yes' if symbol in price_symbols else 'no'}, "
            f"hyphenated {normalized}={'yes' if normalized in price_symbols else 'no'}"
        )


def main():
    missing_files = [
        path for path in (TRANSCRIPT_PATH, PRICE_PATH) if not path.exists()
    ]
    if missing_files:
        paths = "\n".join(f"  {path}" for path in missing_files)
        raise FileNotFoundError(
            f"Raw data file(s) not found:\n{paths}\n"
            "Run python scripts/download_raw_data.py first."
        )

    inspect_transcripts()
    inspect_prices()


if __name__ == "__main__":
    main()
