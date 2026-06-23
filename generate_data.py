import pandas as pd
from datetime import datetime, timedelta
import random
import sqlite3

start_time = datetime(2026, 6, 10, 0, 0, 0)

data = []

for i in range(2000):
    timestamp = start_time + timedelta(minutes=i)

    data.append([
        timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        random.randint(100, 500),   # energy
        random.randint(20, 50),     # temperature
        random.randint(900, 1100),  # pressure
        random.randint(50, 200),    # flow
        random.randint(210, 240)    # voltage
    ])

df = pd.DataFrame(
    data,
    columns=[
        "timestamp",
        "energy",
        "temperature",
        "pressure",
        "flow",
        "voltage"
    ]
)

# Save CSV
df.to_csv("data/input.csv", index=False)

# Save to SQLite
conn = sqlite3.connect("database/aggregation.db")

df.to_sql(
    "raw_timeseries_data",
    conn,
    if_exists="replace",
    index=False
)

conn.close()

print("Data inserted successfully.")