# Nashville Rental Pipeline

Modular pipeline that pulls Nashville rental listings from the RapidAPI Zillow proxy, normalizes the payload, and stores results in SQLite and CSV outputs aligned to a custom Excel schema.

## Requirements
- Python 3.11+
- Packages from `requirements.txt`
- RapidAPI key with access to `zillow-com1`
- Excel schema workbook at `excel_files/nashville-zillow-project.xlsx`

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Export your API key (`setx ZILLOW_RAPIDAPI_KEY "your-key"` on PowerShell or `export` in bash).
3. Confirm the Excel workbook path is `excel_files/nashville-zillow-project.xlsx` or update `db/db_migrator.py`.

## Running
```bash
python main.py
```
The script fetches the configured locations, writes `excel_files/nsh-rentYYYYMMDD.csv`, and replaces the `NashvilleRents01` table in `TESTRENT01.db`.

### Streamlit Dashboard
Visualize the live SQLite data with:
```bash
streamlit run streamlit_app.py
```
Use the sidebar to filter rents, search addresses, and refresh the data cache.

## Project Structure
- `api/zillow_fetcher.py` - API client, pagination, JSON flattening
- `db/db_migrator.py` - schema alignment, CSV export, SQLite persistence
- `db/primary_key_migration.py` - safe utility for cloning the SQLite database and applying the new primary-key schema
- `main.py` - orchestration entry point
- `excel_files/` - schema workbook and generated CSV archives
- `streamlit_app.py` - Streamlit UI that queries the SQLite database in real time

## Primary Key Migration
The SQLite table now enforces a deterministic `RECORD_ID` primary key derived from the unique listing fields (currently `DETAILURL`). Existing databases should be upgraded in a copy first:

```bash
python db/primary_key_migration.py --source TESTRENT01.db
```

The script creates `TESTRENT01_pk_test.db` by default, rebuilds the table with the new primary key, and backfills the identifier for every historical row. Pass `--in-place` if you intentionally want to migrate the original file.
