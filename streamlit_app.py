from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Tuple

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from db.db_migrator import PRIMARY_KEY_COLUMN, SQLITE_DB, TABLE_NAME
from main import fetch_dataframe, main 

SNAPSHOT_PATH = Path(__file__).resolve().parent / "seed_data" / "seed_rentals.csv"


@st.cache_data(ttl=60)
def _load_data(db_path: Path, snapshot_path: Path | None = None) -> Tuple[pd.DataFrame, str]:
    """Load rental data from SQLite, falling back to a bundled snapshot when needed."""
    data_source = "database"
    df = pd.DataFrame()

    if db_path.exists():
        with sqlite3.connect(db_path) as conn:
            try:
                df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)
            except sqlite3.OperationalError:
                df = pd.DataFrame()

    df = _coerce_types(df)

    if df.empty and snapshot_path and snapshot_path.exists():
        df = pd.read_csv(snapshot_path)
        df = _coerce_types(df)
        data_source = "snapshot"

    return df, data_source


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Safety net: ensure numeric columns are properly typed.

    Note: pandas.read_sql may infer object dtype for numeric columns if there
    are any empty strings, even though SQLite stores them with correct types.
    This function ensures proper typing for dashboard operations.
    """
    if df.empty:
        return df

    # Convert numeric columns - pandas may read them as object type due to mixed content
    numeric_columns = [
        "PRICE", "BEDS", "BEDROOMS", "BATHROOMS", "LIVINGAREA",
        "DAYSONZILLOW", "AVAILABILITYCOUNT", "LONGITUDE", "LATITUDE"
    ]
    for column in numeric_columns:
        if column in df.columns:
            # Always convert to ensure proper typing, even if schema is correct
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
    st.title("Nashville Rentals — Live View")

    db_path = Path(SQLITE_DB)
    with st.spinner("Loading rental listings..."):
        df, data_source = _load_data(db_path, SNAPSHOT_PATH)

    if df.empty:
        st.warning("No rental listings are available yet. Refresh or rerun the ingestion pipeline.")
        return

    if data_source == "snapshot":
        st.info("Showing the bundled snapshot. Run an ingestion to refresh with live data.")

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
        # _load_data.clear()
        df, data_source = _load_data(db_path, SNAPSHOT_PATH)

    filtered_df = _filter_dataframe(df, price_range, search_term)
    total, avg_price, latest_ts = _compute_metrics(filtered_df)

    col1, col2, col3 = st.columns(3)
    col1.metric("Listings", f"{total:,}")
    col2.metric("Average Rent", f"${avg_price:,.0f}")
    col3.metric(
        "Latest Ingestion",
        latest_ts.strftime("%Y-%m-%d") if latest_ts else "Unknown",
    )

    st.markdown("---")  # Add a visual separator
    st.subheader("Analytics Dashboard")
    
    power_bi_embed_url = "https://app.powerbi.com/view?r=eyJrIjoiODllYjBkZmQtN2ViOC00NmFmLTlkNWEtNzRmMTNmNTExZGM1IiwidCI6Ijk0NDE5YmE4LWNkZTItNDgxMC1iZDZjLTVmNzRlMWUyODkwYiJ9"
    components.iframe(power_bi_embed_url, height=700)

    st.markdown("---")  # Add another separator before listings

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
