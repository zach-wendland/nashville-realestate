from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Tuple

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from db.db_config import FORSALE_CONFIG, PRIMARY_KEY_COLUMN, RENT_CONFIG, SQLITE_DB
from main_unified import run_forsale_pipeline, run_rent_pipeline, run_all_pipelines

SNAPSHOT_PATH = Path(__file__).resolve().parent / "seed_data" / "seed_rentals.csv"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@st.cache_data(ttl=60)
def _load_data(db_path: Path, table_name: str, snapshot_path: Path | None = None) -> Tuple[pd.DataFrame, str]:
    """Load data from SQLite, falling back to a bundled snapshot when needed."""
    data_source = "database"
    df = pd.DataFrame()

    if db_path.exists():
        with sqlite3.connect(db_path) as conn:
            try:
                # Check if table exists first
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,)
                )
                table_exists = cursor.fetchone() is not None

                if table_exists:
                    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
                else:
                    df = pd.DataFrame()
            except sqlite3.OperationalError as e:
                logging.warning(f"Database error loading {table_name}: {e}")
                df = pd.DataFrame()

    df = _coerce_types(df)

    if df.empty and snapshot_path and snapshot_path.exists():
        df = pd.read_csv(snapshot_path)
        df = _coerce_types(df)
        data_source = "snapshot"

    return df, data_source


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize numeric and datetime columns for dashboard use."""
    if df.empty:
        return df

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
    df: pd.DataFrame,
    price_range: Tuple[float, float],
    search_term: str,
    bedrooms_range: Tuple[int, int] | None = None,
    bathrooms_range: Tuple[float, float] | None = None,
    living_area_range: Tuple[float, float] | None = None,
    property_types: list[str] | None = None,
    max_days_on_zillow: int | None = None,
    listing_statuses: list[str] | None = None,
) -> pd.DataFrame:
    """Apply sidebar filters to the dataframe."""
    filtered = df.copy()

    # Price filter
    if "PRICE" in filtered.columns:
        filtered = filtered[
            (filtered["PRICE"].fillna(0) >= price_range[0])
            & (filtered["PRICE"].fillna(0) <= price_range[1])
        ]

    # Bedrooms filter
    if bedrooms_range and "BEDROOMS" in filtered.columns:
        filtered = filtered[
            (filtered["BEDROOMS"].fillna(0) >= bedrooms_range[0])
            & (filtered["BEDROOMS"].fillna(0) <= bedrooms_range[1])
        ]

    # Bathrooms filter
    if bathrooms_range and "BATHROOMS" in filtered.columns:
        filtered = filtered[
            (filtered["BATHROOMS"].fillna(0) >= bathrooms_range[0])
            & (filtered["BATHROOMS"].fillna(0) <= bathrooms_range[1])
        ]

    # Living area filter
    if living_area_range and "LIVINGAREA" in filtered.columns:
        filtered = filtered[
            (filtered["LIVINGAREA"].fillna(0) >= living_area_range[0])
            & (filtered["LIVINGAREA"].fillna(0) <= living_area_range[1])
        ]

    # Property type filter
    if property_types and "PROPERTYTYPE" in filtered.columns:
        filtered = filtered[filtered["PROPERTYTYPE"].isin(property_types)]

    # Days on Zillow filter
    if max_days_on_zillow is not None and "DAYSONZILLOW" in filtered.columns:
        filtered = filtered[filtered["DAYSONZILLOW"].fillna(0) <= max_days_on_zillow]

    # Listing status filter
    if listing_statuses and "LISTINGSTATUS" in filtered.columns:
        filtered = filtered[filtered["LISTINGSTATUS"].isin(listing_statuses)]

    # Search term filter
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


def _render_listing_view(
    df: pd.DataFrame,
    data_source: str,
    listing_type: str,
    price_label: str,
    csv_filename: str,
    filter_key: str
) -> None:
    """Render the listing view with filters and data display."""
    if df.empty:
        st.warning(f"No {listing_type} listings are available yet. Use the 'Refresh Data' button in the sidebar.")
        return

    if data_source == "snapshot":
        st.info(f"Showing bundled snapshot. Run an ingestion to refresh with live data.")

    # Filters in sidebar
    st.sidebar.header(f"{listing_type} Filters")

    # Price filter
    min_price = float(df["PRICE"].min(skipna=True) or 0)
    max_price = float(df["PRICE"].max(skipna=True) or 5000)
    price_range = st.sidebar.slider(
        price_label,
        min_value=int(min_price) if min_price < max_price else 0,
        max_value=int(max_price) if max_price > min_price else int(min_price) + 1,
        value=(int(min_price), int(max_price)),
        step=50,
        key=f"{filter_key}_price"
    )

    # Bedrooms filter
    if "BEDROOMS" in df.columns:
        min_beds = int(df["BEDROOMS"].min(skipna=True) or 0)
        max_beds = int(df["BEDROOMS"].max(skipna=True) or 10)
        if min_beds < max_beds:
            bedrooms_range = st.sidebar.slider(
                "Bedrooms",
                min_value=min_beds,
                max_value=max_beds,
                value=(min_beds, max_beds),
                step=1,
                key=f"{filter_key}_bedrooms"
            )
        else:
            bedrooms_range = None
    else:
        bedrooms_range = None

    # Bathrooms filter
    if "BATHROOMS" in df.columns:
        min_baths = float(df["BATHROOMS"].min(skipna=True) or 0)
        max_baths = float(df["BATHROOMS"].max(skipna=True) or 6)
        if min_baths < max_baths:
            bathrooms_range = st.sidebar.slider(
                "Bathrooms",
                min_value=min_baths,
                max_value=max_baths,
                value=(min_baths, max_baths),
                step=0.5,
                key=f"{filter_key}_bathrooms"
            )
        else:
            bathrooms_range = None
    else:
        bathrooms_range = None

    # Living Area filter
    if "LIVINGAREA" in df.columns:
        min_sqft = float(df["LIVINGAREA"].min(skipna=True) or 0)
        max_sqft = float(df["LIVINGAREA"].max(skipna=True) or 5000)
        if min_sqft < max_sqft:
            living_area_range = st.sidebar.slider(
                "Living Area (sq ft)",
                min_value=int(min_sqft),
                max_value=int(max_sqft),
                value=(int(min_sqft), int(max_sqft)),
                step=100,
                key=f"{filter_key}_sqft"
            )
        else:
            living_area_range = None
    else:
        living_area_range = None

    # Property Type filter
    if "PROPERTYTYPE" in df.columns:
        property_types_available = sorted(df["PROPERTYTYPE"].dropna().unique().tolist())
        if property_types_available:
            property_types = st.sidebar.multiselect(
                "Property Type",
                options=property_types_available,
                default=property_types_available,
                key=f"{filter_key}_property_type"
            )
        else:
            property_types = None
    else:
        property_types = None

    # Days on Zillow filter
    if "DAYSONZILLOW" in df.columns:
        days_col = pd.to_numeric(df["DAYSONZILLOW"], errors="coerce")
        max_days_available = int(days_col.max(skipna=True) or 365)
        max_days_on_zillow = st.sidebar.slider(
            "Max Days on Zillow",
            min_value=0,
            max_value=max_days_available,
            value=max_days_available,
            step=5,
            key=f"{filter_key}_days_on_zillow"
        )
    else:
        max_days_on_zillow = None

    # Listing Status filter
    if "LISTINGSTATUS" in df.columns:
        listing_statuses_available = sorted(df["LISTINGSTATUS"].dropna().unique().tolist())
        if listing_statuses_available:
            listing_statuses = st.sidebar.multiselect(
                "Listing Status",
                options=listing_statuses_available,
                default=listing_statuses_available,
                key=f"{filter_key}_listing_status"
            )
        else:
            listing_statuses = None
    else:
        listing_statuses = None

    # Search term filter
    search_term = st.sidebar.text_input(
        "Search by address, building, or URL",
        placeholder="e.g. 37206 or 5th Ave",
        key=f"{filter_key}_search"
    )

    # Apply all filters
    filtered_df = _filter_dataframe(
        df,
        price_range,
        search_term,
        bedrooms_range,
        bathrooms_range,
        living_area_range,
        property_types,
        max_days_on_zillow,
        listing_statuses
    )
    total, avg_price, latest_ts = _compute_metrics(filtered_df)

    col1, col2, col3 = st.columns(3)
    col1.metric("Listings", f"{total:,}")
    col2.metric(f"Average {listing_type} Price", f"${avg_price:,.0f}")
    col3.metric(
        "Latest Ingestion",
        latest_ts.strftime("%Y-%m-%d") if latest_ts else "Unknown",
    )

    st.markdown("---")

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
            file_name=csv_filename,
            mime="text/csv",
        )
        st.json(filtered_df.head(25).to_dict(orient="records"))


def main() -> None:
    st.set_page_config(page_title="Nashville Real Estate Dashboard", layout="wide")
    st.title("Nashville Real Estate — Live View")

    db_path = Path(SQLITE_DB)

    # Sidebar refresh controls
    st.sidebar.header("Data Refresh")

    col1, col2 = st.sidebar.columns(2)
    refresh_rent = col1.button("🔄 Refresh Rentals", use_container_width=True)
    refresh_sale = col2.button("🔄 Refresh For-Sale", use_container_width=True)

    refresh_all = st.sidebar.button("🔄 Refresh ALL Data", type="primary", use_container_width=True)

    # Handle refresh actions
    if refresh_all:
        with st.spinner("Fetching all listing data from Zillow API..."):
            try:
                run_all_pipelines()
                _load_data.clear()
                st.sidebar.success("✅ All data refreshed successfully!")
            except Exception as e:
                st.sidebar.error(f"❌ Error refreshing data: {str(e)}")
                logging.error(f"Pipeline error: {e}", exc_info=True)

    elif refresh_rent:
        with st.spinner("Fetching rental listings from Zillow API..."):
            try:
                run_rent_pipeline()
                _load_data.clear()
                st.sidebar.success("✅ Rental data refreshed successfully!")
            except Exception as e:
                st.sidebar.error(f"❌ Error refreshing rental data: {str(e)}")
                logging.error(f"Rental pipeline error: {e}", exc_info=True)

    elif refresh_sale:
        with st.spinner("Fetching for-sale listings from Zillow API..."):
            try:
                run_forsale_pipeline()
                _load_data.clear()
                st.sidebar.success("✅ For-sale data refreshed successfully!")
            except Exception as e:
                st.sidebar.error(f"❌ Error refreshing for-sale data: {str(e)}")
                logging.error(f"ForSale pipeline error: {e}", exc_info=True)

    # Create tabs for different listing types
    tab1, tab2, tab3 = st.tabs(["🏠 Rentals", "🏡 For Sale", "📊 Analytics Dashboard"])

    with tab1:
        with st.spinner("Loading rental listings..."):
            rent_df, rent_source = _load_data(db_path, RENT_CONFIG.table_name, SNAPSHOT_PATH)
        _render_listing_view(
            rent_df,
            rent_source,
            "Rental",
            "Monthly rent",
            "nashville_rentals_filtered.csv",
            "rent"
        )

    with tab2:
        with st.spinner("Loading for-sale listings..."):
            sale_df, sale_source = _load_data(db_path, FORSALE_CONFIG.table_name, None)
        _render_listing_view(
            sale_df,
            sale_source,
            "For-Sale",
            "Sale price",
            "nashville_forsale_filtered.csv",
            "forsale"
        )

    with tab3:
        st.subheader("Analytics Dashboard")
        power_bi_embed_url = "https://app.powerbi.com/view?r=eyJrIjoiODllYjBkZmQtN2ViOC00NmFmLTlkNWEtNzRmMTNmNTExZGM1IiwidCI6Ijk0NDE5YmE4LWNkZTItNDgxMC1iZDZjLTVmNzRlMWUyODkwYiJ9"
        components.iframe(power_bi_embed_url, height=700)


if __name__ == "__main__":
    main()
