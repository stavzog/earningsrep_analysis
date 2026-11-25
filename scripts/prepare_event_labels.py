"""Create auditable stock-versus-RSP return labels."""

# Run after download_eps.py:
# python -m pip install pandas pyarrow exchange-calendars
# python scripts/prepare_event_labels.py

from pathlib import Path

import exchange_calendars as xcals
import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT_PATH = ROOT / "data/raw/transcripts/transcripts_raw.parquet"
PRICE_PATH = ROOT / "data/raw/prices/prices_yfinance_adjusted.parquet"
EPS_PATH = ROOT / "data/raw/eps/eps_yfinance.parquet"
AUDIT_PATH = ROOT / "data/interim/event_labels_audit.parquet"
ELIGIBLE_PATH = ROOT / "data/processed/eligible_event_labels.parquet"

START_YEAR = 2015
END_YEAR = 2025

# Transcript times in these cases are not real call times (for example a
# 23:15 call, or a weekend publication date). Replace them with the nearest
# Yahoo earnings release time for the same ticker within this many days.
YAHOO_WINDOW_DAYS = 7


def find_blank_transcripts(path):
    blank_rows = set()
    row_number = 0

    for batch in pq.ParquetFile(path).iter_batches(
        columns=["content"],
        batch_size=256,
    ):
        for text in batch.column(0).to_pylist():
            if text is None or not text.strip():
                blank_rows.add(row_number)
            row_number += 1

    return blank_rows


def is_suspicious(calendar, call_time):
    call_date = call_time.tz_localize(None).normalize()
    late_night = call_time.hour >= 21 or call_time.hour < 6
    return late_night or not calendar.is_session(call_date)


def load_yahoo_times():
    eps = pd.read_parquet(EPS_PATH, columns=["symbol", "Earnings Date"])
    times = pd.to_datetime(eps["Earnings Date"]).dt.tz_convert(
        "America/New_York"
    )
    # A midnight time means Yahoo gave a date but no release time.
    eps = eps.assign(time=times).loc[times.dt.hour != 0]
    return {
        symbol: rows["time"].drop_duplicates()
        for symbol, rows in eps.groupby("symbol")
    }


def find_yahoo_time(yahoo_times, symbol, call_time):
    times = yahoo_times.get(symbol)
    if times is None:
        return None

    gaps = (times - call_time).abs()
    nearby = gaps.loc[gaps <= pd.Timedelta(days=YAHOO_WINDOW_DAYS)]
    closest = nearby.loc[nearby == nearby.min()]
    if len(closest) != 1:
        return None
    return times.loc[closest.index[0]]


def align_call(calendar, call_time):
    call_date = call_time.tz_localize(None).normalize()

    if not calendar.is_session(call_date):
        event_date = calendar.date_to_session(call_date, direction="next")
        return "non_trading_day", event_date

    market_open = calendar.session_open(call_date)
    market_close = calendar.session_close(call_date)
    call_utc = call_time.tz_convert("UTC")

    if call_utc < market_open:
        return "before_open", call_date
    if call_utc < market_close:
        return "during_market_hours", None
    return "after_close", calendar.next_session(call_date)


def get_price(closes, date, ticker):
    if date is None or ticker not in closes.columns or date not in closes.index:
        return None

    value = closes.at[date, ticker]
    return None if pd.isna(value) else float(value)


def choose_exclusion(row, has_price_history):
    if row["is_blank_transcript"]:
        return "blank_transcript"
    if not has_price_history:
        return "missing_stock_price_history"
    if row["call_timing"] == "suspicious_timestamp":
        return "suspicious_call_timestamp"
    if row["call_timing"] == "during_market_hours":
        return "during_market_hours"
    if row["stock_previous_close"] is None:
        return "missing_stock_previous_close"
    if row["stock_event_close"] is None:
        return "missing_stock_event_close"
    if row["rsp_previous_close"] is None:
        return "missing_rsp_previous_close"
    if row["rsp_event_close"] is None:
        return "missing_rsp_event_close"
    if min(
        row["stock_previous_close"],
        row["stock_event_close"],
        row["rsp_previous_close"],
        row["rsp_event_close"],
    ) <= 0:
        return "nonpositive_price"
    return None


def main():
    transcripts = pd.read_parquet(
        TRANSCRIPT_PATH,
        columns=["symbol", "company_name", "year", "quarter", "date"],
    )
    transcripts.insert(0, "transcript_row", transcripts.index)

    call_times = pd.to_datetime(transcripts["date"], errors="coerce")
    if call_times.isna().any():
        raise ValueError("The transcript data contains invalid timestamps.")

    study_rows = call_times.dt.year.between(START_YEAR, END_YEAR)
    transcripts = transcripts.loc[study_rows].copy()
    call_times = call_times.loc[study_rows].dt.tz_localize(
        "America/New_York",
        ambiguous="NaT",
        nonexistent="NaT",
    )
    if call_times.isna().any():
        raise ValueError("A transcript timestamp could not be localized to ET.")

    prices = pd.read_parquet(PRICE_PATH)
    closes = prices["Close"].copy()
    closes.columns = closes.columns.astype(str)
    closes.index = pd.to_datetime(closes.index).normalize()

    blank_rows = find_blank_transcripts(TRANSCRIPT_PATH)
    calendar = xcals.get_calendar("XNYS")
    yahoo_times = load_yahoo_times()
    records = []

    for index, transcript in transcripts.iterrows():
        symbol = str(transcript["symbol"])
        transcript_time = call_times.loc[index]
        call_time = transcript_time
        call_time_source = "transcript"
        if is_suspicious(calendar, transcript_time):
            call_time = find_yahoo_time(yahoo_times, symbol, transcript_time)
            call_time_source = (
                "yahoo_earnings_date" if call_time is not None else None
            )

        if call_time is None:
            call_timing, event_date = "suspicious_timestamp", None
        else:
            call_timing, event_date = align_call(calendar, call_time)
        previous_date = (
            calendar.previous_session(event_date)
            if event_date is not None
            else None
        )

        row = {
            "event_id": f"{symbol}|{transcript['date']}",
            "transcript_row": transcript["transcript_row"],
            "symbol": symbol,
            "company_name": transcript["company_name"],
            "fiscal_year": transcript["year"],
            "fiscal_quarter": transcript["quarter"],
            "call_timestamp_et": transcript_time,
            "call_time_used_et": call_time,
            "call_time_source": call_time_source,
            "call_timing": call_timing,
            "event_date": event_date,
            "previous_trading_date": previous_date,
            "is_blank_transcript": transcript["transcript_row"] in blank_rows,
            "stock_previous_close": get_price(
                closes, previous_date, symbol
            ),
            "stock_event_close": get_price(closes, event_date, symbol),
            "rsp_previous_close": get_price(closes, previous_date, "RSP"),
            "rsp_event_close": get_price(closes, event_date, "RSP"),
        }

        has_price_history = (
            symbol in closes.columns and closes[symbol].notna().any()
        )
        row["exclusion_reason"] = choose_exclusion(row, has_price_history)

        if (
            row["stock_previous_close"] is not None
            and row["stock_event_close"] is not None
            and row["stock_previous_close"] > 0
        ):
            row["stock_return"] = (
                row["stock_event_close"] / row["stock_previous_close"] - 1
            )
        else:
            row["stock_return"] = None

        if (
            row["rsp_previous_close"] is not None
            and row["rsp_event_close"] is not None
            and row["rsp_previous_close"] > 0
        ):
            row["rsp_return"] = (
                row["rsp_event_close"] / row["rsp_previous_close"] - 1
            )
        else:
            row["rsp_return"] = None

        if row["stock_return"] is not None and row["rsp_return"] is not None:
            row["relative_return"] = (
                row["stock_return"] - row["rsp_return"]
            )
        else:
            row["relative_return"] = None

        row["is_eligible"] = row["exclusion_reason"] is None
        row["label"] = (
            "UP" if row["relative_return"] >= 0 else "DOWN"
        ) if row["is_eligible"] else None
        records.append(row)

    audit = pd.DataFrame(records)
    eligible = audit.loc[audit["is_eligible"]].copy()

    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ELIGIBLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    audit.to_parquet(AUDIT_PATH, index=False)
    eligible.to_parquet(ELIGIBLE_PATH, index=False)

    print(f"Candidate events: {len(audit):,}")
    print(f"Eligible events: {len(eligible):,}")
    print("\nExclusions:")
    print(audit["exclusion_reason"].dropna().value_counts().to_string())
    print("\nCall time source:")
    print(audit["call_time_source"].value_counts(dropna=False).to_string())
    print("\nEligible labels:")
    print(eligible["label"].value_counts().to_string())
    print(f"\nSaved audit data to {AUDIT_PATH}")
    print(f"Saved eligible labels to {ELIGIBLE_PATH}")


if __name__ == "__main__":
    main()
