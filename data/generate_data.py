import pandas as pd
import random
from datetime import datetime, timedelta

rows = []
start = datetime(2025, 1, 1, 0, 0, 0)

for i in range(2000):
    rows.append({
        "machine_id": f"M{random.randint(1,10):03}",
        "timestamp": start + timedelta(minutes=i),
        "production_count": random.randint(50, 200),
        "temperature": round(random.uniform(60, 90), 2),
        "utilization_percent": round(random.uniform(70, 100), 2),
        "downtime_minutes": random.randint(0, 20),
        "defect_count": random.randint(0, 10)
    })

df = pd.DataFrame(rows)
df.to_csv("machine_metrics_2000.csv", index=False)

print("Generated 2000 rows successfully!")