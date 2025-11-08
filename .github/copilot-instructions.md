## Quick orientation

This repository is a small, modular ETL pipeline that fetches rental listings from a RapidAPI proxy for Zillow, normalizes the JSON payload into a flat tabular form, and persists results to a CSV archive and a local SQLite database.

- Entry point: `main.py` — orchestrates fetch -> normalize -> align -> persist.
- API client: `api/zillow_fetcher.py` — builds requests, paginates, flattens nested JSON and units into wide columns.
- Schema & persistence: `db/db_migrator.py` — loads an Excel-driven schema, normalizes column names, writes CSVs and manages SQLite table/index logic.
- Small utilities: `utils/ingestionVars.py` (produces `INGESTION_DATE`) and `excel_files/` (schema workbook + generated CSVs).

## Environment & run commands

- Python 3.11+ (see `README.md`). Install deps with:

  pip install -r requirements.txt

- RapidAPI key required: set `ZILLOW_RAPIDAPI_KEY` (or `RAPIDAPI_KEY`) in your environment. Example (PowerShell):

  setx ZILLOW_RAPIDAPI_KEY "your-key"

- Run the pipeline locally:

  python main.py

Logging is configured in `main.py` with INFO level; increase to DEBUG when needed for low-level traces.

## Important project conventions (do not change lightly)

- Normalized column names: The project uppercases and normalizes column names using `db/db_migrator.normalize_column_names()` before any schema alignment or persistence. Always use that helper when adding or renaming columns.

- Uppercasing values: `uppercase_dataframe(df)` converts cell values to strings and uppercases them before export. This is relied on by downstream schema expectations.

- Schema source of truth: an Excel workbook at `excel_files/nashville-zillow-project.xlsx`, sheet `zillow-rent-schema`. `load_schema()` reads the `needed?` column to decide required fields. If you add a new required column update the workbook or adjust `load_schema()` invocations.

- CSV naming: `db/db_migrator.CSV_PREFIX` (default `nsh-rent`) + UTC date `YYYYMMDD` — files written to `excel_files/`.

- SQLite: default DB is `TESTRENT01.db` and table `NashvilleRents01` (configured in `db/db_migrator.py`). Unique-key logic uses `UNIQUE_KEY_COLUMNS` (`DETAILURL` by default) to dedupe and to update the `INGESTION_DATE` for existing rows.

## Data flow (concrete steps)

1. `main.py` builds `FetchConfig` and calls `api.zillow_fetcher.fetch_dataframe()`.
2. `fetch_dataframe()` -> `collect_properties()` paginates via `iterate_pages()` and `fetch_page()` (rate limit lives in `DEFAULT_RATE_LIMIT_SECONDS` and retries in `DEFAULT_RETRIES`).
3. JSON results are flattened and units are expanded into suffixed columns by `records_to_dataframe()` and `_augment_with_units()`.
4. `main.py` ensures priority unit fallback columns (e.g. `PRICE` from `PRICE_1`) in `_ensure_priority_columns()`.
5. Values are uppercased, schema loaded via `load_schema(extra_columns=["INGESTION_DATE"])`, then `align_to_schema()` reindexes columns to the Excel-driven schema and fills missing values with empty strings.
6. `persist_to_sqlite()` deduplicates using `UNIQUE_KEY_COLUMNS`, updates `INGESTION_DATE` for existing rows if present, and appends new rows.

## Error & edge cases to be aware of

- Missing RapidAPI key -> `ZillowAPIError` from `get_api_key()`.
- Missing Excel schema file -> `FileNotFoundError` from `load_schema()`; keep `excel_files/nashville-zillow-project.xlsx` available for local runs.
- API rate limits -> `fetch_page()` will sleep and retry on 429; default cooldown is 5s.
- Pagination stop conditions: empty results or `totalPages` hint from the API.

## How to modify schema or DB safely

- If you add a required column in the Excel workbook, update the sheet `zillow-rent-schema` and re-run `python main.py` — `load_schema()` will include it.
- To change the SQLite DB path, update `db/db_migrator.SQLITE_DB` or pass a different path to `persist_to_sqlite()` and `ensure_table_exists()`.

## Small coding patterns & tests to reuse

- Use `normalize_column_names()` whenever you create DataFrame columns programmatically so header collision logic stays consistent (it appends `_N` on duplicates).
- Use the existing `_flatten_mapping()` pattern in `zillow_fetcher.py` when converting nested dicts to flat columns.

## Debugging tips

- To inspect raw API payloads, temporarily call `collect_properties()` from an interactive REPL and print a sample `records[:3]`.
- Turn up logging by editing `logging.basicConfig(level=logging.INFO, ...)` in `main.py` to `level=logging.DEBUG`.

## Files to look at for examples

- `main.py` — orchestration, ingestion date handling, and persistence calls.
- `api/zillow_fetcher.py` — API client: `FetchConfig`, `fetch_dataframe()`, flattening and pagination.
- `db/db_migrator.py` — schema loading, normalization, CSV/SQLite persistence and unique-key update logic.

If anything above is unclear or you want additional sections (for example: contributor workflow, unit test guidance, or CI rules), tell me which area to expand and I will iterate.
