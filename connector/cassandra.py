import os

# Database credentials (placeholders that can be updated)
contact_points = os.environ.get("CASSANDRA_CONTACT_POINTS", "127.0.0.1").split(",")
keyspace = os.environ.get("CASSANDRA_KEYSPACE", "sampledb")
username = os.environ.get("CASSANDRA_USERNAME", "")
password = os.environ.get("CASSANDRA_PASSWORD", "")

def get_session():
    from cassandra.cluster import Cluster
    from cassandra.auth import PlainTextAuthProvider
    
    if username and password:
        auth_provider = PlainTextAuthProvider(username=username, password=password)
        cluster = Cluster(contact_points, auth_provider=auth_provider)
    else:
        cluster = Cluster(contact_points)
        
    return cluster.connect(keyspace)

def get_kpis():
    session = get_session()
    rows = session.execute("SELECT production_count, temperature, utilization_percent, downtime_minutes, defect_count FROM machine_metrics")
    
    total_production = 0
    temperatures = []
    utilizations = []
    total_downtime = 0
    total_defects = 0
    
    for r in rows:
        total_production += int(r.production_count or 0)
        if r.temperature is not None:
            temperatures.append(float(r.temperature))
        if r.utilization_percent is not None:
            utilizations.append(float(r.utilization_percent))
        total_downtime += int(r.downtime_minutes or 0)
        total_defects += int(r.defect_count or 0)
        
    avg_temp = round(sum(temperatures) / len(temperatures), 2) if temperatures else 0.0
    avg_util = round(sum(utilizations) / len(utilizations), 2) if utilizations else 0.0
    
    return {
        "total_production": total_production,
        "avg_temperature": avg_temp,
        "avg_utilization": avg_util,
        "total_downtime": total_downtime,
        "total_defects": total_defects
    }

def get_hourly_production():
    session = get_session()
    rows = session.execute("SELECT timestamp, production_count FROM machine_metrics")
    
    grouped = {}
    for r in rows:
        ts_str = str(r.timestamp)
        bucket = ts_str[:13] + ":00:00"
        grouped[bucket] = grouped.get(bucket, 0) + int(r.production_count or 0)
        
    return [{"time_bucket": b, "production": p} for b, p in sorted(grouped.items())]

def get_temperature_trend():
    session = get_session()
    rows = session.execute("SELECT machine_id, temperature, defect_count FROM machine_metrics")
    
    grouped = {}
    for r in rows:
        m_id = r.machine_id
        if m_id:
            grouped.setdefault(m_id, {"temps": [], "defects": 0})
            if r.temperature is not None:
                grouped[m_id]["temps"].append(float(r.temperature))
            grouped[m_id]["defects"] += int(r.defect_count or 0)
            
    return [
        {
            "machine_id": m_id,
            "avg_temp": round(sum(v["temps"])/len(v["temps"]), 2) if v["temps"] else 0.0,
            "defects": v["defects"]
        }
        for m_id, v in sorted(grouped.items())
    ]

def get_utilization_trend():
    session = get_session()
    rows = session.execute("SELECT machine_id, utilization_percent FROM machine_metrics")
    
    grouped = {}
    for r in rows:
        m_id = r.machine_id
        if m_id:
            grouped.setdefault(m_id, [])
            if r.utilization_percent is not None:
                grouped[m_id].append(float(r.utilization_percent))
                
    return [
        {
            "machine_id": m_id,
            "utilization": round(sum(vals)/len(vals), 2) if vals else 0.0
        }
        for m_id, vals in sorted(grouped.items())
    ]