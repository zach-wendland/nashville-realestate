import pandas as pd
import sqlite3 

table_name = "NashvilleRents"

df = pd.read_excel("nashville-zillow-project.xlsx",sheet_name="zillow-rent-schema")

colNames = list(df["name"])
nameNeeded = list(df["needed?"])

df = df.astype(str).applymap(str.upper)

newColNames = []

for cols, names in zip(colNames, nameNeeded):
    if names == "Y":
        newColNames.append(cols)

newColDtypeList = ["TEXT"] * len(newColNames)

schema = dict(zip(newColNames, newColDtypeList))

schema_parts = [f"{col} {dtype}" for col, dtype in zip(newColNames, newColDtypeList)]
schema_sql = ", ".join(schema_parts)

print(schema_sql)

createStmt = f"CREATE TABLE IF NOT EXISTS {table_name} ({schema_sql});"
conn = sqlite3.connect("TESTRENT01.db")
cursor = conn.cursor()
cursor.execute(createStmt)
conn.commit()
conn.close()