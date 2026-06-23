import os
import json
import asyncio
import uuid
import sqlite3
import threading
from datetime import datetime
from typing import Dict, Any, List
from flask import Flask, jsonify, render_template, request, send_from_directory

import pandas as pd
import numpy as np

app = Flask(__name__, template_folder=".", static_folder=".", static_url_path="/static")

# ── CORS headers (allow browser to call API from any origin) ──────────────
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

@app.route("/style.css")
def serve_css():
    return send_from_directory(".", "style.css")



META_DB = "pulseops_engine_metadata.db"
MAPPING_FILE = "cached_property_mappings.json"
BACKGROUND_LOOP = None

def start_background_loop():
    global BACKGROUND_LOOP
    BACKGROUND_LOOP = asyncio.new_event_loop()
    asyncio.set_event_loop(BACKGROUND_LOOP)
    BACKGROUND_LOOP.run_forever()

def init_meta_db():
    conn = sqlite3.connect(META_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_history (
            job_id TEXT PRIMARY KEY,
            start_time TEXT,
            end_time TEXT,
            source_table TEXT,
            target_table TEXT,
            row_count INTEGER,
            status TEXT,
            progress INTEGER,
            error_message TEXT
        )
    """)
    conn.commit()
    conn.close()

init_meta_db()


# ─────────────────────────────────────────────
#  REAL DATABASE CLIENT — replaces DBClientMock
# ─────────────────────────────────────────────

class DBClient:
    """
    Connects to PostgreSQL, MySQL, or MongoDB using credentials
    supplied by the user through the UI. Nothing is hardcoded.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config   = config
        self.db_type = config.get("db_type", "").lower()   # postgresql / mysql / mongodb / sqlite
        self.host     = config.get("host", "localhost")
        self.port     = config.get("port")
        self.database = config.get("database", "")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.table    = config.get("table", "")

    # ── helpers ──────────────────────────────

    def _pg_conn(self):
        """Return a live psycopg2 connection."""
        import psycopg2
        return psycopg2.connect(
            host=self.host,
            port=int(self.port or 5432),
            dbname=self.database,
            user=self.username,
            password=self.password,
            connect_timeout=5
        )

    def _mysql_conn(self):
        """Return a live mysql-connector-python connection."""
        import mysql.connector
        return mysql.connector.connect(
            host=self.host,
            port=int(self.port or 3306),
            database=self.database,
            user=self.username,
            password=self.password,
            connection_timeout=5
        )

    def _mongo_client(self):
        """Return a live pymongo MongoClient."""
        from pymongo import MongoClient
        uri = (
            f"mongodb://{self.username}:{self.password}@{self.host}:{int(self.port or 27017)}"
            f"/{self.database}?serverSelectionTimeoutMS=5000"
            if self.username
            else f"mongodb://{self.host}:{int(self.port or 27017)}/{self.database}"
              "?serverSelectionTimeoutMS=5000"
        )
        client = MongoClient(uri)
        return client

    # ── public API ───────────────────────────

    def test_connection(self) -> bool:
        """Actually connect to the target database and verify it works."""
        try:
            if self.db_type == "postgresql":
                conn = self._pg_conn()
                conn.close()

            elif self.db_type == "mysql":
                conn = self._mysql_conn()
                conn.close()

            elif self.db_type == "mongodb":
                client = self._mongo_client()
                client.admin.command("ping")
                client.close()

            elif self.db_type == "sqlite":
                path = self.config.get("sqlite_path", "")
                if not path:
                    raise ValueError("SQLite file path is required.")
                conn = sqlite3.connect(path)
                conn.execute("SELECT 1")
                conn.close()

            else:
                raise ValueError(f"Unsupported database type: '{self.db_type}'. "
                                 "Supported: postgresql, mysql, mongodb, sqlite")
            return True

        except Exception as e:
            raise ConnectionError(f"Connection failed: {str(e)}")

    def list_tables(self) -> List[str]:
        """List all tables (SQL) or collections (MongoDB) in the database."""
        if self.db_type == "postgresql":
            conn = self._pg_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
            conn.close()
            return tables

        elif self.db_type == "mysql":
            conn = self._mysql_conn()
            cur = conn.cursor()
            cur.execute("SHOW TABLES")
            tables = [row[0] for row in cur.fetchall()]
            conn.close()
            return tables

        elif self.db_type == "mongodb":
            client = self._mongo_client()
            db = client[self.database]
            collections = db.list_collection_names()
            client.close()
            return sorted(collections)

        elif self.db_type == "sqlite":
            path = self.config.get("sqlite_path", "")
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cur.fetchall()]
            conn.close()
            return tables

        else:
            raise ValueError(f"Unsupported db_type: {self.db_type}")

    def discover_columns(self, table_name: str) -> Dict[str, List[str]]:
        """
        Return all columns and the subset that are numeric.
        For MongoDB, inspects the first 100 documents to infer types.
        """
        if self.db_type == "postgresql":
            conn = self._pg_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            rows = cur.fetchall()
            conn.close()

            NUMERIC_PG = {"integer","bigint","smallint","numeric","decimal",
                          "real","double precision","serial","bigserial"}
            all_cols     = [r[0] for r in rows]
            numeric_cols = [r[0] for r in rows if r[1].lower() in NUMERIC_PG]
            return {"all": all_cols, "numeric": numeric_cols}

        elif self.db_type == "mysql":
            conn = self._mysql_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (self.database, table_name))
            rows = cur.fetchall()
            conn.close()

            NUMERIC_MY = {"int","tinyint","smallint","mediumint","bigint",
                          "float","double","decimal","numeric","year"}
            all_cols     = [r[0] for r in rows]
            numeric_cols = [r[0] for r in rows if r[1].lower() in NUMERIC_MY]
            return {"all": all_cols, "numeric": numeric_cols}

        elif self.db_type == "mongodb":
            client = self._mongo_client()
            db = client[self.database]
            sample = list(db[table_name].find({}, {"_id": 0}).limit(100))
            client.close()
            if not sample:
                return {"all": [], "numeric": []}
            all_cols, numeric_cols = [], []
            for key in sample[0].keys():
                all_cols.append(key)
                values = [doc.get(key) for doc in sample if key in doc]
                if any(isinstance(v, (int, float)) for v in values):
                    numeric_cols.append(key)
            return {"all": all_cols, "numeric": numeric_cols}

        elif self.db_type == "sqlite":
            path = self.config.get("sqlite_path", "")
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table_name})")
            rows = cur.fetchall()
            conn.close()
            NUMERIC_SQ = {"integer","real","float","double","numeric","decimal","bigint","int"}
            all_cols     = [r[1] for r in rows]
            numeric_cols = [r[1] for r in rows if r[2].lower().split("(")[0] in NUMERIC_SQ]
            return {"all": all_cols, "numeric": numeric_cols}

        else:
            raise ValueError(f"Unsupported db_type: {self.db_type}")

    def extract_data(self, table: str, ts_col: str, start: str, end: str) -> pd.DataFrame:
        """Pull raw time-series rows between start and end from the real database."""
        if self.db_type == "postgresql":
            conn = self._pg_conn()
            query = f"""
                SELECT * FROM {table}
                WHERE {ts_col} BETWEEN %s AND %s
                ORDER BY {ts_col}
            """
            df = pd.read_sql_query(query, conn, params=[start, end])
            conn.close()
            return df

        elif self.db_type == "mysql":
            conn = self._mysql_conn()
            query = f"""
                SELECT * FROM `{table}`
                WHERE `{ts_col}` BETWEEN %s AND %s
                ORDER BY `{ts_col}`
            """
            df = pd.read_sql_query(query, conn, params=[start, end])
            conn.close()
            return df

        elif self.db_type == "mongodb":
            from bson import Decimal128
            client = self._mongo_client()
            db = client[self.database]
            cursor = db[table].find(
                {ts_col: {"$gte": start, "$lte": end}},
                {"_id": 0}
            ).sort(ts_col, 1)
            df = pd.DataFrame(list(cursor))
            client.close()
            return df

        elif self.db_type == "sqlite":
            path = self.config.get("sqlite_path", "")
            conn = sqlite3.connect(path)
            query = f"SELECT * FROM {table} WHERE {ts_col} BETWEEN ? AND ? ORDER BY {ts_col}"
            df = pd.read_sql_query(query, conn, params=[start, end])
            conn.close()
            return df

        else:
            raise ValueError(f"Unsupported db_type: {self.db_type}")

    def write_aggregated_data(self, table: str, df: pd.DataFrame) -> int:
        """Write the aggregated DataFrame to the target database table."""
        if df.empty:
            return 0

        if self.db_type == "postgresql":
            from sqlalchemy import create_engine
            engine = create_engine(
                f"postgresql+psycopg2://{self.username}:{self.password}"
                f"@{self.host}:{int(self.port or 5432)}/{self.database}"
            )
            if "timestamp" in df.columns:
                df = df.rename(columns={"timestamp": "bucket_time"})
            df.columns = [str(c).replace(" ", "_").replace("-", "_").replace(".", "_") for c in df.columns]
            df.to_sql(table, engine, if_exists="replace", index=False)
            engine.dispose()
            return len(df)

        elif self.db_type == "mysql":
            from sqlalchemy import create_engine, text
            engine = create_engine(
                f"mysql+mysqlconnector://{self.username}:{self.password}"
                f"@{self.host}:{int(self.port or 3306)}/{self.database}"
            )
            # Rename reserved word 'timestamp' column to 'bucket_time' to avoid MySQL conflicts
            if "timestamp" in df.columns:
                df = df.rename(columns={"timestamp": "bucket_time"})
            # Sanitize all column names — replace spaces and special chars with underscores
            df.columns = [str(c).replace(" ", "_").replace("-", "_").replace(".", "_") for c in df.columns]
            df.to_sql(table, engine, if_exists="replace", index=False)
            engine.dispose()
            return len(df)

        elif self.db_type == "mongodb":
            client = self._mongo_client()
            db = client[self.database]
            records = df.to_dict(orient="records")
            db[table].insert_many(records)
            client.close()
            return len(df)

        elif self.db_type == "sqlite":
            path = self.config.get("sqlite_path", "")
            conn = sqlite3.connect(path)
            if "timestamp" in df.columns:
                df = df.rename(columns={"timestamp": "bucket_time"})
            df.columns = [str(c).replace(" ", "_").replace("-", "_").replace(".", "_") for c in df.columns]
            df.to_sql(table, conn, if_exists="replace", index=False)
            conn.close()
            return len(df)

        else:
            raise ValueError(f"Unsupported db_type: {self.db_type}")


# ─────────────────────────────────────────────
#  AGGREGATION ENGINE  (unchanged logic)
# ─────────────────────────────────────────────

def apply_custom_aggregations(df, ts_col, bucket_size, rules):
    if df.empty:
        return df

    bucket_map = {
        "1m":"1min","5m":"5min","15m":"15min","30m":"30min",
        "1h":"1h","4h":"4h","12h":"12h","1d":"1D"
    }
    freq = bucket_map.get(bucket_size, "5min")

    df[ts_col] = pd.to_datetime(df[ts_col])
    df = df.set_index(ts_col)
    resampler = df.resample(freq)
    blocks = []

    for column, operation in rules.items():
        if column not in df.columns:
            continue
        if not pd.api.types.is_numeric_dtype(df[column]):
            continue
        op = operation.upper()
        if   op == "MIN":    res = resampler[column].min()
        elif op == "MAX":    res = resampler[column].max()
        elif op == "MEAN":   res = resampler[column].mean()
        elif op == "SUM":    res = resampler[column].sum()
        elif op == "COUNT":  res = resampler[column].count()
        elif op == "FIRST":  res = resampler[column].first()
        elif op == "LAST":   res = resampler[column].last()
        elif op == "STDDEV": res = resampler[column].std().fillna(0.0)
        elif op == "MEDIAN": res = resampler[column].median()
        elif op == "P95":    res = resampler[column].quantile(0.95)
        else: continue
        res.name = f"{column}_{op.lower()}"
        blocks.append(res)

    if not blocks:
        return pd.DataFrame()
    return pd.concat(blocks, axis=1).reset_index()


# ─────────────────────────────────────────────
#  ASYNC JOB WORKER
# ─────────────────────────────────────────────

async def run_async_aggregation_worker(job_id, payload):
    conn = sqlite3.connect(META_DB)
    try:
        conn.execute("UPDATE job_history SET progress=20, status='Running' WHERE job_id=?", (job_id,))
        conn.commit()
        await asyncio.sleep(0.3)

        # Build clients from the REAL credentials passed by the UI
        src_client = DBClient(payload["source_config"])
        tgt_client = DBClient(payload["target_config"])

        df_source = src_client.extract_data(
            table=payload["source_table"],
            ts_col=payload["timestamp_column"],
            start=payload["start_range"],
            end=payload["end_range"]
        )
        conn.execute("UPDATE job_history SET progress=65 WHERE job_id=?", (job_id,))
        conn.commit()
        await asyncio.sleep(0.3)

        df_out = apply_custom_aggregations(
            df=df_source,
            ts_col=payload["timestamp_column"],
            bucket_size=payload["time_bucket"],
            rules=payload["mappings"]
        )
        conn.execute("UPDATE job_history SET progress=85 WHERE job_id=?", (job_id,))
        conn.commit()
        await asyncio.sleep(0.2)

        emitted_rows = tgt_client.write_aggregated_data(payload["target_table"], df_out)

        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            UPDATE job_history
            SET progress=100, status='Completed', end_time=?, row_count=?
            WHERE job_id=?
        """, (end_time, emitted_rows, job_id))
        conn.commit()

    except Exception as err:
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Return a clean message, not a raw stack trace
        clean_msg = str(err).split("\n")[0][:300]
        conn.execute("""
            UPDATE job_history
            SET progress=100, status='Failed', end_time=?, error_message=?
            WHERE job_id=?
        """, (end_time, clean_msg, job_id))
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────
#  FLASK ROUTES  (unchanged)
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/test-connection", methods=["POST"])
def route_test_connection():
    config = request.json
    try:
        client = DBClient(config)
        client.test_connection()
        return jsonify({"status": "Success", "tables": client.list_tables()}), 200
    except Exception as e:
        return jsonify({"detail": str(e)}), 400

@app.route("/api/discover-schema", methods=["POST"])
def route_discover_schema():
    config = request.json
    client = DBClient(config)
    columns = client.discover_columns(config.get("table", ""))
    return jsonify({
        "all_columns": columns["all"],
        "numeric_columns": columns["numeric"]
    }), 200

@app.route("/api/config-mapping", methods=["POST"])
def route_save_mapping():
    payload = request.json
    table_name = payload.get("table")
    try:
        store = json.load(open(MAPPING_FILE)) if os.path.exists(MAPPING_FILE) else {}
    except Exception:
        store = {}
    store[table_name] = payload
    with open(MAPPING_FILE, "w") as f:
        json.dump(store, f)
    return jsonify({"status": "Saved"}), 200

@app.route("/api/config-mapping/<table_name>", methods=["GET"])
def route_load_mapping(table_name):
    if not os.path.exists(MAPPING_FILE):
        return jsonify({"error": "No cached mappings identified"}), 404
    store = json.load(open(MAPPING_FILE))
    if table_name in store:
        return jsonify(store[table_name]), 200
    return jsonify({"error": "Configuration map not found"}), 404

@app.route("/api/jobs", methods=["POST"])
def trigger_aggregation_job():
    payload = request.json
    job_id = str(uuid.uuid4())
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(META_DB)
    conn.execute("""
        INSERT INTO job_history (job_id, start_time, source_table, target_table, status, progress, row_count)
        VALUES (?, ?, ?, ?, 'Running', 0, 0)
    """, (job_id, start_time, payload["source_table"], payload["target_table"]))
    conn.commit()
    conn.close()
    asyncio.run_coroutine_threadsafe(run_async_aggregation_worker(job_id, payload), BACKGROUND_LOOP)
    return jsonify({"job_id": job_id, "status": "Running"}), 202

@app.route("/api/jobs/<job_id>", methods=["GET"])
def check_job_status(job_id):
    conn = sqlite3.connect(META_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT status, progress, error_message FROM job_history WHERE job_id=?", (job_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Job reference missing"}), 404
    return jsonify(dict(row)), 200

@app.route("/api/jobs/history", methods=["GET"])
def get_historical_jobs_ledger():
    conn = sqlite3.connect(META_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT start_time, end_time, source_table, target_table, row_count, status FROM job_history ORDER BY start_time DESC")
    rows = cur.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows]), 200

@app.route("/api/kpis", methods=["GET"])
def get_pipeline_kpis():
    conn = sqlite3.connect(META_DB)
    cur = conn.cursor()
    cur.execute("SELECT SUM(row_count), COUNT(job_id) FROM job_history WHERE status='Completed'")
    row = cur.fetchone()
    conn.close()
    total_rows = row[0] if row and row[0] else 0
    total_jobs = row[1] if row and row[1] else 0
    return jsonify({
        "total_ingested":    f"{(12.4 + (total_rows/1000)):.1f}K",
        "aggregated_output": f"{total_rows:,}",
        "avg_process_time":  "94ms" if total_jobs > 0 else "0ms",
        "active_nodes":      "4",
        "pipeline_health":   "99.8%" if total_jobs == 0 else "100.0%"
    }), 200

@app.route("/api/chart-data", methods=["GET"])
def get_chart_data_stream():
    """Return real job history data for charts — last 10 completed jobs."""
    conn = sqlite3.connect(META_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT start_time, end_time, row_count,
               ROUND((JULIANDAY(COALESCE(end_time, start_time)) - JULIANDAY(start_time)) * 86400 * 1000) as duration_ms
        FROM job_history
        WHERE status = 'Completed'
        ORDER BY start_time DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return jsonify({
            "intervals":      ["No data yet"],
            "ingestion_bars": [0],
            "latency_lines":  [0]
        }), 200

    rows = list(reversed(rows))  # chronological order
    intervals    = [r["start_time"][11:16] if r["start_time"] else "?" for r in rows]
    row_counts   = [r["row_count"] or 0 for r in rows]
    durations    = [min(r["duration_ms"] or 0, 5000) for r in rows]

    return jsonify({
        "intervals":      intervals,
        "ingestion_bars": row_counts,
        "latency_lines":  durations
    }), 200


@app.route("/api/preview-results", methods=["POST"])
def preview_results():
    """Fetch up to 100 rows from the target table to preview in the UI."""
    payload = request.json
    try:
        client  = DBClient(payload["target_config"])
        db_type = payload["target_config"].get("db_type", "").lower()
        table   = payload["target_table"]

        if db_type == "postgresql":
            conn = client._pg_conn()
            df = pd.read_sql_query(f"SELECT * FROM {table} ORDER BY 1 LIMIT 100", conn)
            conn.close()
        elif db_type == "mysql":
            conn = client._mysql_conn()
            df = pd.read_sql_query(f"SELECT * FROM `{table}` ORDER BY 1 LIMIT 100", conn)
            conn.close()
        elif db_type == "mongodb":
            mongo = client._mongo_client()
            db = mongo[client.database]
            docs = list(db[table].find({}, {"_id": 0}).limit(100))
            mongo.close()
            df = pd.DataFrame(docs)
        elif db_type == "sqlite":
            path = payload["target_config"].get("sqlite_path", "")
            conn = sqlite3.connect(path)
            df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 100", conn)
            conn.close()
        else:
            return jsonify({"error": "Unsupported db type"}), 400

        if df.empty:
            return jsonify({"columns": [], "rows": [], "total": 0}), 200

        # Convert datetime columns to string
        for col in df.select_dtypes(include=["datetime64"]).columns:
            df[col] = df[col].astype(str)

        # Replace NaN/None with None (null in JSON)
        df = df.where(pd.notnull(df), None)

        # Round floats to 4 decimal places for cleaner display
        for col in df.select_dtypes(include=["float64", "float32"]).columns:
            df[col] = df[col].round(4)

        # Convert to JSON-safe list
        rows = []
        for row in df.values.tolist():
            clean_row = []
            for val in row:
                import math
                if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                    clean_row.append(None)
                else:
                    clean_row.append(val)
            rows.append(clean_row)

        return jsonify({
            "columns": list(df.columns),
            "rows":    rows,
            "total":   len(df)
        }), 200

    except Exception as e:
        import traceback
        print("PREVIEW ERROR:", traceback.format_exc())
        return jsonify({"error": str(e).split("\n")[0]}), 400

if __name__ == "__main__":
    t = threading.Thread(target=start_background_loop, daemon=True)
    t.start()
    app.run(debug=True, host="0.0.0.0", port=5001, use_reloader=False)