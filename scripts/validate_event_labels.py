"""Check label calculations and print a small sample for manual review."""

# Run after prepare_event_labels.py:
# python scripts/validate_event_labels.py

import math
from datetime import time
from pathlib import Path

import exchange_calendars as xcals
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "data/interim/event_labels_audit.parquet"
SAMPLE_SIZE = 2
SAMPLE_COLUMNS = [
    "event_id",
    "call_timestamp_et",
    "call_timing",
    "event_date",
    "previous_trading_date",
    "stock_previous_close",
    "stock_event_close",
    "rsp_previous_close",
    "rsp_event_close",
    "stock_return",
    "rsp_return",
    "relative_return",
    "label",
    "exclusion_reason",
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_row(row, calendar):
    event_id = row["event_id"]
    call_time = row["call_timestamp_et"]
    call_date = call_time.tz_localize(None).normalize()
    event_date = row["event_date"]
    timing = row["call_timing"]

    if timing == "non_trading_day":
        require(not calendar.is_session(call_date), f"{event_id}: bad timing")
        expected_event = calendar.date_to_session(call_date, direction="next")
    else:
        require(calendar.is_session(call_date), f"{event_id}: bad call date")
        market_open = calendar.session_open(call_date)
        market_close = calendar.session_close(call_date)
        call_utc = call_time.tz_convert("UTC")

        if timing == "before_open":
            require(call_utc < market_open, f"{event_id}: not before open")
            expected_event = call_date
        elif timing == "during_market_hours":
            require(
                market_open <= call_utc < market_close,
                f"{event_id}: not during market hours",
            )
            require(pd.isna(event_date), f"{event_id}: should have no event date")
            return
        elif timing == "after_close":
            require(call_utc >= market_close, f"{event_id}: not after close")
            expected_event = calendar.next_session(call_date)
        else:
            raise ValueError(f"{event_id}: unknown call timing {timing}")

    require(event_date == expected_event, f"{event_id}: wrong event date")
    require(
        row["previous_trading_date"]
        == calendar.previous_session(expected_event),
        f"{event_id}: wrong previous trading date",
    )

    if not row["is_eligible"]:
        return

    stock_return = (
        row["stock_event_close"] / row["stock_previous_close"] - 1
    )
    rsp_return = row["rsp_event_close"] / row["rsp_previous_close"] - 1
    relative_return = stock_return - rsp_return

    require(
        math.isclose(row["stock_return"], stock_return),
        f"{event_id}: wrong stock return",
    )
    require(
        math.isclose(row["rsp_return"], rsp_return),
        f"{event_id}: wrong RSP return",
    )
    require(
        math.isclose(row["relative_return"], relative_return),
        f"{event_id}: wrong relative return",
    )

    expected_label = "UP" if relative_return >= 0 else "DOWN"
    require(row["label"] == expected_label, f"{event_id}: wrong label")


def print_sample(title, rows):
    print(f"\n{title}")
    if rows.empty:
        print("No matching events.")
        return

    sample = rows.sample(
        n=min(SAMPLE_SIZE, len(rows)),
        random_state=7,
    )
    print(sample[SAMPLE_COLUMNS].to_string(index=False))


def main():
    audit = pd.read_parquet(AUDIT_PATH)
    calendar = xcals.get_calendar("XNYS")

    require(audit["event_id"].is_unique, "Event IDs are not unique.")
    require(
        audit["is_eligible"].equals(audit["exclusion_reason"].isna()),
        "Eligibility and exclusion reasons disagree.",
    )

    for _, row in audit.iterrows():
        validate_row(row, calendar)

    print(f"Validated {len(audit):,} events successfully.")

    for timing in [
        "before_open",
        "after_close",
        "non_trading_day",
        "during_market_hours",
    ]:
        print_sample(
            timing.replace("_", " ").title(),
            audit.loc[audit["call_timing"] == timing],
        )

    for label in ["UP", "DOWN"]:
        print_sample(
            f"Eligible {label} labels",
            audit.loc[audit["label"] == label],
        )

    print_sample(
        "Missing stock-price history",
        audit.loc[
            audit["exclusion_reason"] == "missing_stock_price_history"
        ],
    )
    print_sample(
        "Missing previous close",
        audit.loc[
            audit["exclusion_reason"] == "missing_stock_previous_close"
        ],
    )

    early_close_rows = []
    boundary_rows = []
    for index, row in audit.iterrows():
        call_time = row["call_timestamp_et"]
        call_date = call_time.tz_localize(None).normalize()
        if not calendar.is_session(call_date):
            continue

        market_open = calendar.session_open(call_date)
        market_close = calendar.session_close(call_date)
        call_utc = call_time.tz_convert("UTC")
        close_et = market_close.tz_convert("America/New_York").time()

        if close_et < time(16):
            early_close_rows.append(index)
        if call_utc == market_open or call_utc == market_close:
            boundary_rows.append(index)

    print_sample("Calls on early-close days", audit.loc[early_close_rows])
    print_sample("Calls exactly at open or close", audit.loc[boundary_rows])


if __name__ == "__main__":
    main()
