from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Tuple

import pandas as pd
import streamlit as st

from db.db_migrator import PRIMARY_KEY_COLUMN, SQLITE_DB, TABLE_NAME


@st.cache_data(ttl=60)
def _load_data(db_path: Path) -> pd.DataFrame:
    """Load the latest rental data from SQLite with basic type coercion."""
    if not db_path.exists():
        return pd.DataFrame()

    with sqlite3.connect(db_path) as conn:
        try:
            df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)
        except sqlite3.OperationalError:
            return pd.DataFrame()

    numeric_columns = ["PRICE", "BEDS", "BEDROOMS", "BATHROOMS", "LIVINGAREA"]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "INGESTION_DATE" in df.columns:
        df["INGESTION_DATE"] = pd.to_datetime(
            df["INGESTION_DATE"], format="%Y%m%d", errors="coerce"
        )
    return df


def _filter_dataframe(
    df: pd.DataFrame, price_range: Tuple[float, float], search_term: str
) -> pd.DataFrame:
    """Apply sidebar filters to the dataframe."""
    filtered = df.copy()
    if "PRICE" in filtered.columns:
        filtered = filtered[
            (filtered["PRICE"].fillna(0) >= price_range[0])
            & (filtered["PRICE"].fillna(0) <= price_range[1])
        ]
    if search_term:
        search_upper = search_term.strip().upper()
        mask = pd.Series(False, index=filtered.index)
        for column in ("DETAILURL", "ADDRESS", "BUILDINGNAME"):
            if column in filtered.columns:
                mask |= filtered[column].fillna("").str.contains(search_upper, case=False)
        filtered = filtered[mask]
    return filtered


def _compute_metrics(df: pd.DataFrame) -> Tuple[int, float, datetime | None]:
    """Return count, average price, and latest ingestion timestamp."""
    total = len(df)
    avg_price = float(df["PRICE"].mean()) if "PRICE" in df.columns and total else 0.0
    latest_ts: datetime | None = None
    if "INGESTION_DATE" in df.columns and not df["INGESTION_DATE"].isna().all():
        latest_ts = df["INGESTION_DATE"].max()
    return total, avg_price, latest_ts


def main() -> None:
    st.set_page_config(page_title="Nashville Rentals Dashboard", layout="wide")
    st.title("Nashville Rentals – Live View")
    st.caption(f"SQLite source: `{SQLITE_DB}` · Table: `{TABLE_NAME}`")

    db_path = Path(SQLITE_DB)
    with st.spinner("Loading data from SQLite…"):
        df = _load_data(db_path)

    if df.empty:
        st.warning("No data available yet. Run `python main.py` to ingest listings.")
        return

    st.sidebar.header("Filters")
    min_price = float(df["PRICE"].min(skipna=True) or 0)
    max_price = float(df["PRICE"].max(skipna=True) or 5000)
    price_range = st.sidebar.slider(
        "Monthly rent",
        min_value=int(min_price) if min_price < max_price else 0,
        max_value=int(max_price) if max_price > min_price else int(min_price) + 1,
        value=(int(min_price), int(max_price)),
        step=50,
    )
    search_term = st.sidebar.text_input(
        "Search by address, building, or URL",
        placeholder="e.g. 37206 or 5th Ave",
    )
    if st.sidebar.button("Refresh data"):
        _load_data.clear()
        df = _load_data(db_path)

    filtered_df = _filter_dataframe(df, price_range, search_term)
    total, avg_price, latest_ts = _compute_metrics(filtered_df)

    col1, col2, col3 = st.columns(3)
    col1.metric("Listings", f"{total:,}")
    col2.metric("Average Rent", f"${avg_price:,.0f}")
    col3.metric(
        "Latest Ingestion",
        latest_ts.strftime("%Y-%m-%d") if latest_ts else "Unknown",
    )

    st.subheader("Listings")
    st.dataframe(
        filtered_df.sort_values(
            by=["INGESTION_DATE", PRIMARY_KEY_COLUMN]
            if "INGESTION_DATE" in filtered_df.columns
            else PRIMARY_KEY_COLUMN,
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Raw JSON / CSV export"):
        st.download_button(
            "Download filtered CSV",
            filtered_df.to_csv(index=False),
            file_name="nashville_rentals_filtered.csv",
            mime="text/csv",
        )
        st.json(filtered_df.head(25).to_dict(orient="records"))


if __name__ == "__main__":
    main()
