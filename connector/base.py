import json
from pathlib import Path
from statistics import mean
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "data.json"


def load_records() -> List[Dict]:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def aggregate_metrics(records: List[Dict]) -> Dict:
    total_production = sum(int(item.get("production_count", 0)) for item in records)
    avg_temperature = round(mean([float(item.get("temperature", 0)) for item in records]), 2) if records else 0
    avg_utilization = round(mean([float(item.get("utilization_percent", 0)) for item in records]), 2) if records else 0
    total_downtime = sum(int(item.get("downtime_minutes", 0)) for item in records)
    total_defects = sum(int(item.get("defect_count", 0)) for item in records)
    return {
        "total_production": total_production,
        "avg_temperature": avg_temperature,
        "avg_utilization": avg_utilization,
        "total_downtime": total_downtime,
        "total_defects": total_defects,
    }


def aggregate_series(records: List[Dict], group_by: str, value_key: str, label_key: str = None):
    grouped = {}
    for item in records:
        key = item.get(group_by)
        if key not in grouped:
            grouped[key] = {"label": item.get(label_key or group_by), "value": 0, "count": 0}
        grouped[key]["value"] += float(item.get(value_key, 0))
        grouped[key]["count"] += 1

    series = []
    for key in sorted(grouped):
        entry = grouped[key]
        if entry["count"]:
            series.append({
                "label": entry["label"],
                "value": round(entry["value"] / entry["count"], 2) if value_key in {"temperature", "utilization_percent"} else entry["value"],
            })
    return series


def get_hourly_production_series():
    records = load_records()
    return [
        {
            "label": item["timestamp"][:13] + ":00",
            "value": int(item["production_count"]),
        }
        for item in records
    ]


def get_daily_temperature_series():
    records = load_records()
    grouped = {}
    for item in records:
        day = item["timestamp"][:10]
        grouped.setdefault(day, []).append(float(item["temperature"]))
    return [{"label": day, "value": round(sum(vals) / len(vals), 2)} for day, vals in sorted(grouped.items())]


def get_daily_utilization_series():
    records = load_records()
    grouped = {}
    for item in records:
        day = item["timestamp"][:10]
        grouped.setdefault(day, []).append(float(item["utilization_percent"]))
    return [{"label": day, "value": round(sum(vals) / len(vals), 2)} for day, vals in sorted(grouped.items())]
