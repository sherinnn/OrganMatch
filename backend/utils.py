from datetime import datetime
import random

def simulate_viability_check(organ_data):
    """Simulate organ viability checking"""
    organ_type = organ_data.get("type", "heart").lower()
    donation_time = organ_data.get("donation_time")
    temperature = organ_data.get("temperature", 4)
    condition_score = organ_data.get("condition_score", 85)

    # Calculate hours elapsed
    if donation_time:
        try:
            donation_dt = datetime.fromisoformat(donation_time.replace('Z', '+00:00'))
            current_dt = datetime.now()
            hours_elapsed = (current_dt - donation_dt).total_seconds() / 3600
        except:
            hours_elapsed = 0
    else:
        hours_elapsed = 0

    # Viability logic
    max_hours = {"heart": 6, "liver": 12, "kidney": 24, "lung": 8}.get(organ_type, 6)
    temp_factor = 1.0 if temperature <= 4 else 0.7
    condition_factor = condition_score / 100

    hours_left = max(0, (max_hours - hours_elapsed) * temp_factor * condition_factor)
    is_viable = hours_left > 0.5

    return {
        "is_viable": is_viable,
        "hours_left": round(hours_left, 1),
        "hours_elapsed": round(hours_elapsed, 1),
        "max_hours": max_hours,
        "recommendation": "Proceed with transport" if is_viable else "Consider alternative options",
        "urgency": "High" if hours_left < 2 else "Medium" if hours_left < 4 else "Low",
        "method": "simulation"
    }


def simulate_weather_data(location):
    """Simulate weather data"""
    return {
        "temperature_c": 15,
        "condition": "Clear",
        "wind_kph": 12,
        "visibility_km": 10,
        "humidity": 65,
        "transport_suitability": "Excellent",
        "location": location,
        "method": "simulation"
    }


def simulate_flight_search(origin, destination, date=None):
    """Simulate flight search"""
    flights = [
        {
            "flight": f"AA{123 + hash(origin) % 900}",
            "departure": "14:30",
            "arrival": "18:45",
            "duration": "6h 15m",
            "aircraft": "Boeing 737",
            "price": "$450"
        },
        {
            "flight": f"DL{456 + hash(destination) % 900}",
            "departure": "16:00",
            "arrival": "20:30",
            "duration": "6h 30m",
            "aircraft": "Airbus A320",
            "price": "$380"
        },
        {
            "flight": f"UA{789 + hash(origin + destination) % 900}",
            "departure": "18:15",
            "arrival": "22:45",
            "duration": "6h 30m",
            "aircraft": "Boeing 757",
            "price": "$420"
        }
    ]

    return {
        "flights": flights,
        "fastest_flight": flights[0]["flight"],
        "cheapest_flight": flights[1]["flight"],
        "recommendation": f"Book {flights[0]['flight']} for fastest transport",
        "method": "simulation"
    }


def simulate_donor_matching(donor_data, recipient_data):
    """Simulate donor-recipient matching"""
    blood_match = donor_data.get("blood_type") == recipient_data.get("blood_type")
    base_score = 85 if blood_match else 20
    age_factor = max(0, 100 - abs(donor_data.get("age", 30) - recipient_data.get("age", 40)))

    match_score = min(100, (base_score + age_factor) / 2)
    is_compatible = match_score > 70

    return {
        "is_compatible": is_compatible,
        "match_score": round(match_score, 1),
        "blood_type_match": blood_match,
        "tissue_compatibility": "Excellent" if match_score > 85 else "Good" if match_score > 70 else "Poor",
        "recommendation": "Proceed with transplant" if is_compatible else "Consider alternative recipients",
        "method": "simulation"
    }
