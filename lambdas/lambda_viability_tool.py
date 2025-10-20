import json
from datetime import datetime

def lambda_handler(event, context):
    body = event.get("body")
    if isinstance(body, str):
        body = json.loads(body)

    organ_type = body["organ_type"].lower()
    time_of_death = datetime.fromisoformat(body["time_of_death"])
    current_time = datetime.fromisoformat(body["current_time"])
    temperature_c = body["temperature_c"]
    condition_score = body["organ_condition_score"]

    hours_elapsed = (current_time - time_of_death).total_seconds() / 3600
    limits = {"heart": 4, "lung": 6, "liver": 12, "kidney": 24, "pancreas": 12}
    max_hours = limits.get(organ_type, 8)

    adjusted = max_hours - max(0, (temperature_c - 4)) * 0.25
    viability = max(0, min(1, (adjusted - hours_elapsed) / adjusted))
    status = "viable" if viability > 0.3 and condition_score > 50 else "non-viable"

    return {
        "statusCode": 200,
        "body": json.dumps({
            "organ_type": organ_type,
            "hours_elapsed": round(hours_elapsed, 2),
            "viability_score": round(viability, 2),
            "status": status
        })
    }
