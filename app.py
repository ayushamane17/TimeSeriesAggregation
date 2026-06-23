import os
import uuid
import threading
import sqlite3
import pandas as pd
import time
import datetime
from flask import Flask, render_template, request, send_file, jsonify


# Importing core engine logic matching assignment specification

from aggregation.engine import run_aggregation
import inspect

print("FUNCTION:", run_aggregation)
print("SIGNATURE:", inspect.signature(run_aggregation))

from connectors import get_connector

app = Flask(__name__)



# Shared Global Progress Tracking Memory Cache store

job_store = {}



def _parse_port(port_val, default_port=5432):

    if port_val is None or str(port_val).strip() == "":

        return default_port

    try:

        return int(port_val)

    except (ValueError, TypeError):

        return default_port



def _build_config(data):

    db_type = data.get("db_type", "sqlite").lower()

    port_defaults = {

        "sqlite": 0,

        "postgresql": 5432,

        "mysql": 3306,

        "mongodb": 27017,

        "cassandra": 9042  # Fully supported as required by Scope 3.1

    }

    return db_type, {

        "db_type":  db_type,

        "host":     data.get("host", "localhost"),

        "port":     _parse_port(data.get("port"), port_defaults.get(db_type, 5432)),

        "database": data.get("database", ""),

        "username": data.get("username", ""),

        "password": data.get("password", ""), # Sent securely per session, not cached plaintext in UI

    }



## --- API Routes: KPI Metrics Endpoint ---

@app.route("/api/get_kpis", methods=["GET"])

def get_kpis():

    try:

        db_path = os.path.join("database", "aggregation.db")

        if not os.path.exists(db_path):

            return jsonify({"total": 0, "completed": 0, "failed": 0, "rows": 0, "avg_duration": 0})



        with sqlite3.connect(db_path) as conn:

            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_history'")

            if not cursor.fetchone():

                return jsonify({"total": 0, "completed": 0, "failed": 0, "rows": 0, "avg_duration": 0})

           

            df = pd.read_sql_query("SELECT status, rows_read, duration FROM job_history", conn)

            return jsonify({

                "total": int(len(df)),

                "completed": int(len(df[df['status'] == 'Completed'])),

                "failed": int(len(df[df['status'] == 'Failed'])),

                "rows": int(df['rows_read'].sum() if 'rows_read' in df.columns else 0),

                "avg_duration": round(float(df['duration'].mean() if 'duration' in df.columns else 0), 2)

            })

    except Exception as e:

        return jsonify({"error": str(e)}), 500



## --- API Routes: Database Connectors Handshakes ---

@app.route("/test_connection", methods=["POST"])

def test_connection():

    data = request.json or {}

    try:

        db_type, config = _build_config(data)

        connector = get_connector(db_type, config)

        return jsonify(connector.test_connection())

    except Exception as e:

        return jsonify({"success": False, "message": str(e)})



@app.route("/get_tables", methods=["POST"])

def get_tables():

    data = request.json or {}

    try:

        db_type, config = _build_config(data)

        connector = get_connector(db_type, config)

        return jsonify({"tables": connector.get_tables()})

    except Exception as e:

        return jsonify({"tables": [], "error": str(e)})



@app.route("/get_columns", methods=["POST"])

def get_columns():

    data = request.json or {}

    try:

        db_type, config = _build_config(data)

        connector  = get_connector(db_type, config)

        table_name = data.get("table")

        return jsonify({"columns": connector.get_columns(table_name)})

    except Exception as e:

        return jsonify({"columns": [], "error": str(e)})



## --- Background Thread Asynchronous Core Worker Processing ---

def _run_job_thread(job_id, payload):

    try:

        job_store[job_id]["status"] = "Running"

       

        src_db_type, src_config = _build_config(payload["source_config"])

        src_connector = get_connector(src_db_type, src_config)



        tgt_db_type, tgt_config = _build_config(payload["target_config"])

        tgt_connector = get_connector(tgt_db_type, tgt_config)



        # Dynamic fallback target table auto-generation

        target_table = payload.get("target_table") or f"aggregation_{int(time.time())}"

       

        # Pulling the key assignment granular column rule configurations mapping dictionary

        property_rules = payload.get("property_rules", {})
        
        

        run_aggregation(

            property_rules=property_rules,

            interval=payload.get("interval", "h"),

            source_connector=src_connector,

            target_connector=tgt_connector,

            source_table=payload.get("source_table"),

            target_table=target_table,

            timestamp_col=payload.get("timestamp_col"),

            job_id=job_id,

            job_store=job_store,

            date_from=payload.get("date_from"),

            date_to=payload.get("date_to")

        )

       

        # Ensure status reflects accurately if backend doesn't explicitly rewrite it

        if job_store[job_id]["status"] not in ["Completed", "Failed"]:

            job_store[job_id].update({"status": "Completed", "progress": 100})

           

    except Exception as e:

        # Catch and display friendly error descriptions, avoiding raw stack traces in the UI

        job_store[job_id].update({"status": "Failed", "message": str(e), "progress": 100})



@app.route("/run", methods=["POST"])

def run():

    data = request.json or {}

    job_id = str(uuid.uuid4())[:8] # Clean tracking slice id

    job_store[job_id] = {"progress": 0, "status": "Queued", "message": "Starting pipeline extraction..."}

   

    # Asynchronous thread processing guarantees the UI doesn't block or freeze

    thread = threading.Thread(target=_run_job_thread, args=(job_id, data), daemon=True)

    thread.start()

    return jsonify({"success": True, "job_id": job_id})



@app.route("/job_status/<job_id>")

def job_status(job_id):

    job = job_store.get(job_id)

    if not job:

        return jsonify({"error": "Job instance index lookup failure."}), 404

    return jsonify(job)



## --- Data Viewers & History Logs Management ---

@app.route("/all_data")

def all_data():

    db_path = os.path.join("database", "aggregation.db")

    if not os.path.exists(db_path):

         return "<h1>No Database Context Initialized Yet</h1>"

    with sqlite3.connect(db_path) as conn:

        df = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)

        return f"<h1>Data Tables Boundary Preview</h1>{df.to_html(classes='table')}"



@app.route("/history")
def history():
    db_path = os.path.join("database", "aggregation.db")

    if not os.path.exists(db_path):
         return "<h1>JOB History</h1><p>No Log Entries Exist Yet</p>"

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM job_history ORDER BY start_time DESC",
            conn
        )
        return f"""
<html>
<head>
    <title>JOB History</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
        }}

        .back-btn {{
            display: inline-block;
            padding: 10px 15px;
            background: #2563eb;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin-bottom: 15px;
        }}

        table {{
            border-collapse: collapse;
            width: 100%;
        }}

        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
        }}

        th {{
            background: #f1f5f9;
        }}
    </style>
</head>
<body>

    <a href="/" class="back-btn">← Back to Dashboard</a>

    <h1>JOB History</h1>

    {df.to_html(index=False)}

</body>
</html>
"""

    



@app.route("/history/download")

def history_download():

    db_path = os.path.join("database", "aggregation.db")

    df = pd.read_sql_query("SELECT * FROM job_history ORDER BY start_time DESC", sqlite3.connect(db_path))

   

    out_dir = "output"

    os.makedirs(out_dir, exist_ok=True)

    path = os.path.join(out_dir, "job_history.csv")

   

    df.to_csv(path, index=False)

    return send_file(path, as_attachment=True, download_name="job_history.csv")



@app.route("/")

def index():

    return render_template("index.html")



if __name__ == "__main__":

    # Ensure system environment storage contexts are established cleanly

    os.makedirs("database", exist_ok=True)

    os.makedirs("output", exist_ok=True)
    app.run(debug=True)