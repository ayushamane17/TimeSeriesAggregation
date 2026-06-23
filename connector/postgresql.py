import os

# Database credentials (placeholders that can be updated)
host = os.environ.get("POSTGRES_HOST", "localhost")
user = os.environ.get("POSTGRES_USER", "postgres")
password = os.environ.get("POSTGRES_PASSWORD", "postgres")
database = os.environ.get("POSTGRES_DB", "sampledb")
port = os.environ.get("POSTGRES_PORT", "5432")

def get_connection():
    import psycopg2
    import psycopg2.extras
    return psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        cursor_factory=psycopg2.extras.DictCursor
    )

def get_kpis():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(production_count), 0) AS total_production,
                    COALESCE(ROUND(AVG(temperature), 2), 0) AS avg_temperature,
                    COALESCE(ROUND(AVG(utilization_percent), 2), 0) AS avg_utilization,
                    COALESCE(SUM(downtime_minutes), 0) AS total_downtime,
                    COALESCE(SUM(defect_count), 0) AS total_defects
                FROM machine_metrics;
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
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    TO_CHAR(timestamp, 'YYYY-MM-DD HH24:00:00') AS time_bucket,
                    COALESCE(SUM(production_count), 0) AS production
                FROM machine_metrics
                GROUP BY time_bucket
                ORDER BY time_bucket;
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
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    machine_id,
                    COALESCE(ROUND(AVG(temperature), 2), 0) AS avg_temp,
                    COALESCE(SUM(defect_count), 0) AS defects
                FROM machine_metrics
                GROUP BY machine_id
                ORDER BY machine_id;
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
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    machine_id,
                    COALESCE(ROUND(AVG(utilization_percent), 2), 0) AS utilization
                FROM machine_metrics
                GROUP BY machine_id
                ORDER BY machine_id;
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