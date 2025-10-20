from flask import Blueprint, request, jsonify
from backend.core import OrganMatchBackend
from backend.core import donors_table, recipients_table, hospitals_table
import boto3
import os   
backend = OrganMatchBackend()
from dotenv import load_dotenv


load_dotenv()

# --- AWS Configuration ---
REGION = os.getenv("REGION")
api_bp = Blueprint('api', __name__, url_prefix='/api')
s3_client = boto3.client("s3", region_name=REGION)
S3_BUCKET = "organmatch-flight-data"
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")



@api_bp.route('/transport-plan', methods=['POST'])
def create_transport_plan():
    """Generate transport plan using flight data from S3 and weather API"""
    try:
        data = request.get_json()
        origin = data.get('origin', 'SFO')
        destination = data.get('destination', 'BOS')

        # ---------------------------
        # 1️⃣ Fetch mock flights from S3
        # ---------------------------
        s3_response = s3_client.get_object(Bucket=S3_BUCKET, Key="mock_flights.json")
        flights_data = json.loads(s3_response['Body'].read().decode('utf-8'))

        # Filter flights based on origin/destination
        filtered_flights = [
            f for f in flights_data
            if f["from"].lower() == origin.lower() and f["to"].lower() == destination.lower()
        ]

        # Limit to top 5 flights
        flights = filtered_flights[:5] if filtered_flights else []

        # ---------------------------
        # 2️⃣ Get weather info for both cities
        # ---------------------------
        def get_weather(city):
            url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city}"
            try:
                r = requests.get(url)
                data = r.json()
                return {
                    "city": city,
                    "temperature_c": data["current"]["temp_c"],
                    "condition": data["current"]["condition"]["text"],
                    "wind_kph": data["current"]["wind_kph"],
                    "humidity": data["current"]["humidity"]
                }
            except Exception as e:
                return {"city": city, "error": str(e)}

        weather_origin = get_weather(origin)
        weather_dest = get_weather(destination)

        # ---------------------------
        # 3️⃣ Create response object
        # ---------------------------
        plan = {
            "route": {
                "origin": origin,
                "destination": destination,
                "distance": f"{round(0.621 * 1000)} miles",  # placeholder
                "estimatedTime": f"{flights[0]['duration_hr'] if flights else 'N/A'} hours"
            },
            "flights": flights,
            "weather": {
                "origin": weather_origin,
                "destination": weather_dest
            },
            "logistics": {
                "coolerType": "Advanced Perfusion System",
                "estimatedViabilityAtArrival": "90%",
                "backupOptions": 2,
                "medicalTeamReady": True,
                "timestamp": datetime.now().isoformat()
            }
        }

        return jsonify(plan)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# Get all donors/organs
# -------------------------------
@api_bp.route('/organs', methods=['GET'])
def get_organs():
    """Fetch and map donor data from DynamoDB"""
    try:
        response = donors_table.scan()
        items = response.get("Items", [])[:5]  # limit to 5
        mapped = []
        for d in items:
            mapped.append({
                "id": d.get("donor_id", d.get("id", "N/A")),
                "type": d.get("organ_type", d.get("type", "Unknown")),
                "bloodType": d.get("blood_type", "Unknown"),
                "age": int(d.get("age", 0)),
                "conditionScore": float(d.get("organ_condition_score", d.get("condition_score", 0))),
                "location": d.get("hospital_id", d.get("location", "Unknown"))
            })
        return jsonify(mapped)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/recipients', methods=['GET'])
def get_recipients():
    """Fetch and map recipient data from DynamoDB"""
    try:
        response = recipients_table.scan()
        items = response.get("Items", [])[:5]  # limit to 5
        mapped = []
        for r in items:
            mapped.append({
                "id": r.get("recipient_id", r.get("id", "N/A")),
                "name": r.get("name", "Unknown"),
                "bloodType": r.get("blood_type", "Unknown"),
                "age": int(r.get("age", 0)),
                "urgency": r.get("urgency_level", "Medium"),
                "waitTime": f"{r.get('wait_time_days', 0)} days",
                "hospital": r.get("hospital_id", r.get("hospital", "Unknown")),
                "condition": r.get("medical_condition_score", "N/A")
            })
        return jsonify(mapped)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# Get all hospitals
# -------------------------------
@api_bp.route('/hospitals', methods=['GET'])
def get_hospitals():
    try:
        response = hospitals_table.scan()
        items = response.get("Items", [])
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/check-viability', methods=['POST'])
def check_viability():
    data = request.get_json()
    organ = data.get('organ', {})
    return jsonify(backend.check_viability(organ))

@api_bp.route('/get-weather', methods=['POST'])
def get_weather():
    data = request.get_json()
    return jsonify(backend.get_weather(data.get('location', 'Boston')))

@api_bp.route('/search-flights', methods=['POST'])
def search_flights():
    data = request.get_json()
    origin = data.get('origin', 'BOS')
    destination = data.get('destination', 'LAX')
    return jsonify(backend.search_flights(origin, destination, data.get('date')))

@api_bp.route('/match-compatibility', methods=['POST'])
def match_compatibility():
    data = request.get_json()
    donor = data.get('donor', {})
    recipient = data.get('recipient', {})
    return jsonify(backend.match_donor_recipient(donor, recipient))

@api_bp.route('/agent-chat', methods=['POST'])
def agent_chat():
    data = request.get_json()
    msg = data.get('message', '')
    context = data.get('context', {})
    return jsonify(backend.invoke_agent(msg, context))

# Keep adding your other API endpoints here (analytics, hospitals, transport, etc.)
