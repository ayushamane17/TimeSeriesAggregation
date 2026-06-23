import json
import os
import sqlite3
from pathlib import Path
import pymysql

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
JSON_FILE = DATA_DIR / "data.json"
SQL_FILE = DATA_DIR / "data.sql"
SQLITE_FILE = DATA_DIR / "database.sqlite"

# MySQL Credentials
mysql_config = {
    "host": "localhost",
    "user": "root",
    "password": "root"
}

def setup_data():
    print("Step 1: Reading original data...")
    if not JSON_FILE.exists():
        print(f"Error: {JSON_FILE} not found!")
        return None
        
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    # Slicing to exactly 25 records
    reduced_records = records[:25]
    print(f"Reduced records to {len(reduced_records)} items.")
    
    # Save back to data.json
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(reduced_records, f, indent=2)
    print("Saved reduced records to data.json.")
    
    # Generate data.sql
    sql_lines = [
        "CREATE DATABASE IF NOT EXISTS sampledb;",
        "USE sampledb;",
        "DROP TABLE IF EXISTS machine_metrics;",
        "CREATE TABLE machine_metrics (",
        "    id INT PRIMARY KEY AUTO_INCREMENT,",
        "    machine_id VARCHAR(20),",
        "    timestamp DATETIME,",
        "    production_count INT,",
        "    temperature DECIMAL(5,2),",
        "    utilization_percent DECIMAL(5,2),",
        "    downtime_minutes INT,",
        "    defect_count INT",
        ");",
        "",
        "INSERT INTO machine_metrics (machine_id,timestamp,production_count,temperature,utilization_percent,downtime_minutes,defect_count)",
        "VALUES"
    ]
    
    values_list = []
    for r in reduced_records:
        val_str = (
            f"('{r['machine_id']}', "
            f"'{r['timestamp']}', "
            f"{r['production_count']}, "
            f"{r['temperature']}, "
            f"{r['utilization_percent']}, "
            f"{r['downtime_minutes']}, "
            f"{r['defect_count']})"
        )
        values_list.append(val_str)
        
    # Combine values separated by commas, ending with semicolon
    sql_lines.append(",\n".join(values_list) + ";")
    
    with open(SQL_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_lines))
    print("Saved reduced SQL inserts to data.sql.")
    return reduced_records

def setup_sqlite(records):
    print("Step 2: Setting up SQLite...")
    if SQLITE_FILE.exists():
        os.remove(SQLITE_FILE)
        
    conn = sqlite3.connect(str(SQLITE_FILE))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE machine_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT,
            timestamp TEXT,
            production_count INTEGER,
            temperature REAL,
            utilization_percent REAL,
            downtime_minutes INTEGER,
            defect_count INTEGER
        );
    """)
    
    for r in records:
        cursor.execute("""
            INSERT INTO machine_metrics (machine_id, timestamp, production_count, temperature, utilization_percent, downtime_minutes, defect_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            r['machine_id'],
            r['timestamp'],
            r['production_count'],
            r['temperature'],
            r['utilization_percent'],
            r['downtime_minutes'],
            r['defect_count']
        ))
        
    conn.commit()
    conn.close()
    print("SQLite setup complete and saved to data/database.sqlite.")

def setup_mysql(records):
    print("Step 3: Setting up MySQL database 'sampledb'...")
    try:
        conn = pymysql.connect(
            host=mysql_config["host"],
            user=mysql_config["user"],
            password=mysql_config["password"]
        )
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS sampledb;")
        cursor.execute("USE sampledb;")
        cursor.execute("DROP TABLE IF EXISTS machine_metrics;")
        cursor.execute("""
            CREATE TABLE machine_metrics (
                id INT PRIMARY KEY AUTO_INCREMENT,
                machine_id VARCHAR(20),
                timestamp DATETIME,
                production_count INT,
                temperature DECIMAL(5,2),
                utilization_percent DECIMAL(5,2),
                downtime_minutes INT,
                defect_count INT
            );
        """)
        
        for r in records:
            cursor.execute("""
                INSERT INTO machine_metrics (machine_id, timestamp, production_count, temperature, utilization_percent, downtime_minutes, defect_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                r['machine_id'],
                r['timestamp'],
                r['production_count'],
                r['temperature'],
                r['utilization_percent'],
                r['downtime_minutes'],
                r['defect_count']
            ))
        conn.commit()
        conn.close()
        print("MySQL 'sampledb' and 'machine_metrics' loaded successfully.")
    except Exception as e:
        print(f"Warning: Could not connect to MySQL to populate it: {e}")
        print("Skipping live MySQL population. You can import data.sql manually if needed.")

if __name__ == "__main__":
    records = setup_data()
    if records:
        setup_sqlite(records)
        setup_mysql(records)
        print("Data initialization script completed successfully.")
