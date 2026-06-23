import os

# Database credentials (placeholders that can be updated)
mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
db_name = os.environ.get("MONGO_DB", "sampledb")
collection_name = os.environ.get("MONGO_COLLECTION", "machine_metrics")

def get_collection():
    import pymongo
    client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
    db = client[db_name]
    return db[collection_name]

def get_kpis():
    coll = get_collection()
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_production": {"$sum": "$production_count"},
                "avg_temperature": {"$avg": "$temperature"},
                "avg_utilization": {"$avg": "$utilization_percent"},
                "total_downtime": {"$sum": "$downtime_minutes"},
                "total_defects": {"$sum": "$defect_count"}
            }
        }
    ]
    results = list(coll.aggregate(pipeline))
    if not results:
        return {
            "total_production": 0,
            "avg_temperature": 0.0,
            "avg_utilization": 0.0,
            "total_downtime": 0,
            "total_defects": 0
        }
    doc = results[0]
    return {
        "total_production": int(doc.get("total_production", 0)),
        "avg_temperature": round(float(doc.get("avg_temperature", 0)), 2),
        "avg_utilization": round(float(doc.get("avg_utilization", 0)), 2),
        "total_downtime": int(doc.get("total_downtime", 0)),
        "total_defects": int(doc.get("total_defects", 0))
    }

def get_hourly_production():
    coll = get_collection()
    pipeline = [
        {
            "$project": {
                "time_bucket": {"$concat": [{"$substrCP": ["$timestamp", 0, 13]}, ":00:00"]},
                "production_count": 1
            }
        },
        {
            "$group": {
                "_id": "$time_bucket",
                "production": {"$sum": "$production_count"}
            }
        },
        {
            "$sort": {"_id": 1}
        }
    ]
    return [
        {
            "time_bucket": item["_id"],
            "production": int(item["production"])
        }
        for item in coll.aggregate(pipeline)
    ]

def get_temperature_trend():
    coll = get_collection()
    pipeline = [
        {
            "$group": {
                "_id": "$machine_id",
                "avg_temp": {"$avg": "$temperature"},
                "defects": {"$sum": "$defect_count"}
            }
        },
        {
            "$sort": {"_id": 1}
        }
    ]
    return [
        {
            "machine_id": item["_id"],
            "avg_temp": round(float(item["avg_temp"]), 2),
            "defects": int(item["defects"])
        }
        for item in coll.aggregate(pipeline)
    ]

def get_utilization_trend():
    coll = get_collection()
    pipeline = [
        {
            "$group": {
                "_id": "$machine_id",
                "utilization": {"$avg": "$utilization_percent"}
            }
        },
        {
            "$sort": {"_id": 1}
        }
    ]
    return [
        {
            "machine_id": item["_id"],
            "utilization": round(float(item["utilization"]), 2)
        }
        for item in coll.aggregate(pipeline)
    ]