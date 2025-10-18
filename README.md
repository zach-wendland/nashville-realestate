# Nashville Rental Pipeline

Modular data pipeline that pulls Nashville rental listings from the RapidAPI Zillow proxy, normalizes the results, and stores them in both SQLite and CSV outputs aligned to a custom Excel schema.

## Requirements
- Python 3.11+
- Packages from `requirements.txt`
- RapidAPI key with access to `zillow-com1`
- Excel schema file at `excel_files/nashville-zillow-project.xlsx`

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Export your API key, e.g. PowerShell `setx ZILLOW_RAPIDAPI_KEY "your-key"` or `export` in bash.
3. Confirm the Excel workbook path matches `excel_files/nashville-zillow-project.xlsx` or adjust `db/db_migrator.py`.

## Running
```bash
python main.py
```
The script fetches listings for the locations configured in `main.py`, writes a CSV named `nsh-rentYYYYMMDD.csv`, and replaces the `NashvilleRents01` table in `TESTRENT01.db`.

## Project Structure
- `api/zillow_fetcher.py` – API client, pagination, and JSON flattening
- `db/db_migrator.py` – schema alignment, CSV export, SQLite persistence
- `main.py` – orchestration entry point
- `excel_files/` – schema workbook and generated CSV archives
