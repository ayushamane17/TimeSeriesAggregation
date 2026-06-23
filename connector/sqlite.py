import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "database.sqlite"

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def get_kpis():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COALESCE(SUM(production_count), 0) AS total_production,
                COALESCE(ROUND(AVG(temperature), 2), 0) AS avg_temperature,
                COALESCE(ROUND(AVG(utilization_percent), 2), 0) AS avg_utilization,
                COALESCE(SUM(downtime_minutes), 0) AS total_downtime,
                COALESCE(SUM(defect_count), 0) AS total_defects
            FROM machine_metrics
        """)
        result = cursor.fetchone()
        return {
            "total_production": int(result["total_production"]),
            "avg_temperature": float(result["avg_temperature"]),
            "avg_utilization": float(result["avg_utilization"]),
            "total_downtime": int(result["total_downtime"]),
            "total_defects": int(result["total_defects"]),
        }
    finally:
        conn.close()

def get_hourly_production():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                strftime('%Y-%m-%d %H:00:00', timestamp) AS time_bucket,
                COALESCE(SUM(production_count), 0) AS production
            FROM machine_metrics
            GROUP BY time_bucket
            ORDER BY time_bucket
        """)
        rows = cursor.fetchall()
        return [
            {
                "time_bucket": row["time_bucket"],
                "production": int(row["production"])
            }
            for row in rows
        ]
    finally:
        conn.close()

def get_temperature_trend():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                machine_id,
                COALESCE(ROUND(AVG(temperature), 2), 0) AS avg_temp,
                COALESCE(SUM(defect_count), 0) AS defects
            FROM machine_metrics
            GROUP BY machine_id
            ORDER BY machine_id
        """)
        rows = cursor.fetchall()
        return [
            {
                "machine_id": row["machine_id"],
                "avg_temp": float(row["avg_temp"]),
                "defects": int(row["defects"])
            }
            for row in rows
        ]
    finally:
        conn.close()

def get_utilization_trend():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                machine_id,
                COALESCE(ROUND(AVG(utilization_percent), 2), 0) AS utilization
            FROM machine_metrics
            GROUP BY machine_id
            ORDER BY machine_id
        """)
        rows = cursor.fetchall()
        return [
            {
                "machine_id": row["machine_id"],
                "utilization": float(row["utilization"])
            }
            for row in rows
        ]
    finally:
        conn.close()