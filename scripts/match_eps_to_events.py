"""Match yfinance EPS rows to eligible events and report coverage."""

# Run after prepare_event_labels.py:
# python scripts/match_eps_to_events.py

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ELIGIBLE_PATH = ROOT / "data/processed/eligible_event_labels.parquet"
EPS_PATH = ROOT / "data/raw/eps/eps_yfinance.parquet"
OUTPUT_PATH = ROOT / "data/interim/event_eps.parquet"

# An EPS row matches a call when its earnings date is on the call date or up
# to this many calendar days before it. Rows dated after the call are never
# used, so no event can see EPS published after its call.
MATCH_WINDOW_DAYS = 3

EPS_COLUMNS = {
    "Earnings Date": "eps_date",
    "EPS Estimate": "eps_estimate",
    "Reported EPS": "reported_eps",
    "Surprise(%)": "surprise_pct",
}
FIELDS = ["eps_estimate", "reported_eps", "surprise_pct"]

# Model input: surprise %, capped so near-zero estimates cannot produce extreme
# values. Missing surprise is set to 0 (results met expectations).
SURPRISE_CAP = 100


def to_et_date(timestamps):
    timestamps = pd.to_datetime(timestamps)
    if timestamps.dt.tz is not None:
        timestamps = timestamps.dt.tz_convert("America/New_York")
        timestamps = timestamps.dt.tz_localize(None)
    return timestamps.dt.normalize()


def split_name(year):
    if year <= 2022:
        return "train"
    if year == 2023:
        return "validation"
    return "test"


def main():
    events = pd.read_parquet(
        ELIGIBLE_PATH,
        columns=["event_id", "symbol", "call_time_used_et"],
    )
    events["call_date"] = to_et_date(events["call_time_used_et"])
    events["year"] = events["call_date"].dt.year
    events["split"] = events["year"].map(split_name)

    eps = pd.read_parquet(EPS_PATH)
    eps = eps[["symbol", *EPS_COLUMNS]].rename(columns=EPS_COLUMNS)
    eps["eps_date"] = to_et_date(eps["eps_date"])
    duplicate_rows = eps.duplicated().sum()
    eps = eps.drop_duplicates()

    pairs = events[["event_id", "symbol", "call_date"]].merge(eps, on="symbol")
    days_before_call = (pairs["call_date"] - pairs["eps_date"]).dt.days
    after_call_only = set(
        pairs.loc[days_before_call.between(-MATCH_WINDOW_DAYS, -1), "event_id"]
    )

    # Keep the closest EPS date inside the window. If several different rows
    # share that date, the match is ambiguous and none of them is used.
    candidates = pairs.loc[days_before_call.between(0, MATCH_WINDOW_DAYS)]
    closest = candidates.groupby("event_id")["eps_date"].transform("max")
    candidates = candidates.loc[candidates["eps_date"] == closest]
    rows_per_event = candidates["event_id"].value_counts()
    ambiguous_ids = set(rows_per_event.index[rows_per_event > 1])
    matched = candidates.loc[~candidates["event_id"].isin(ambiguous_ids)]

    result = events.merge(
        matched[["event_id", "eps_date", *FIELDS]],
        on="event_id",
        how="left",
    )
    tickers_with_eps = set(eps["symbol"])
    result["eps_match_status"] = "matched"
    result.loc[result["eps_date"].isna(), "eps_match_status"] = (
        "no_eps_row_near_call"
    )
    result.loc[result["event_id"].isin(ambiguous_ids), "eps_match_status"] = (
        "ambiguous_eps_match"
    )
    result.loc[~result["symbol"].isin(tickers_with_eps), "eps_match_status"] = (
        "no_eps_history_for_ticker"
    )

    result["eps_surprise_missing"] = result["surprise_pct"].isna()
    result["eps_surprise_feature"] = (
        result["surprise_pct"].clip(-SURPRISE_CAP, SURPRISE_CAP).fillna(0)
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.drop(columns=["call_date"]).to_parquet(OUTPUT_PATH, index=False)

    unmatched = result["eps_match_status"] != "matched"
    print(f"Eligible events: {len(result):,}")
    print(f"Tickers with EPS rows: {len(tickers_with_eps)}")
    print(f"Exact duplicate EPS rows dropped: {duplicate_rows}")
    print(f"Match window: call date and {MATCH_WINDOW_DAYS} days before")
    print("\nMatch status:")
    print(result["eps_match_status"].value_counts().to_string())
    print(
        "\nUnmatched events with an EPS row 1 to "
        f"{MATCH_WINDOW_DAYS} days after the call: "
        f"{result.loc[unmatched, 'event_id'].isin(after_call_only).sum()}"
    )

    coverage = result[FIELDS].notna()
    print("\nShare of eligible events with each field, by split:")
    print(coverage.groupby(result["split"]).mean().round(3).to_string())
    print("\nShare of eligible events with each field, by year:")
    print(coverage.groupby(result["year"]).mean().round(3).to_string())
    capped = result["surprise_pct"].abs() > SURPRISE_CAP
    print(f"\nSurprise values capped at +/-{SURPRISE_CAP}%: {capped.sum()}")
    print(
        "Missing surprise set to 0: "
        f"{result['eps_surprise_missing'].sum()}"
    )
    print(f"\nSaved matched EPS data to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
