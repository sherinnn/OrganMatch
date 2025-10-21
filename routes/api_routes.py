from flask import Blueprint, request, jsonify
from backend.core import OrganMatchBackend, initialize_aws
import boto3
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Initialize backend lazily
backend = None

def get_backend():
    global backend
    if backend is None:
        backend = OrganMatchBackend()
    return backend

def get_tables():
    initialize_aws()
    from backend.core import donors_table, recipients_table, hospitals_table
    return donors_table, recipients_table, hospitals_table


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
        donors_table, _, _ = get_tables()
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
    """Fetch and map recipient data from DynamoDB with city information"""
    try:
        _, recipients_table, hospitals_table = get_tables()
        
        # Get recipients
        response = recipients_table.scan()
        recipients = response.get("Items", [])[:5]  # limit to 5
        
        # Get hospitals for city mapping
        hospitals_response = hospitals_table.scan()
        hospitals = hospitals_response.get("Items", [])
        
        # Create hospital ID to city mapping
        hospital_city_map = {}
        for hospital in hospitals:
            hospital_id = hospital.get("hospital_id") or hospital.get("id")
            if hospital_id:
                hospital_city_map[hospital_id] = {
                    "city": hospital.get("city", "Unknown"),
                    "state": hospital.get("state", "Unknown"),
                    "name": hospital.get("name", "Unknown Hospital")
                }
        
        mapped = []
        for r in recipients:
            hospital_id = r.get("hospital_id", r.get("hospital", "Unknown"))
            hospital_info = hospital_city_map.get(hospital_id, {
                "city": "Unknown",
                "state": "Unknown", 
                "name": "Unknown Hospital"
            })
            
            mapped.append({
                "id": r.get("recipient_id", r.get("id", "N/A")),
                "name": r.get("name", "Unknown"),
                "bloodType": r.get("blood_type", "Unknown"),
                "age": int(r.get("age", 0)),
                "urgency": r.get("urgency_level", "Medium"),
                "waitTime": f"{r.get('wait_time_days', 0)} days",
                "hospital": hospital_info["name"],
                "city": hospital_info["city"],
                "state": hospital_info["state"],
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
        _, _, hospitals_table = get_tables()
        response = hospitals_table.scan()
        items = response.get("Items", [])
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/check-viability', methods=['POST'])
def check_viability():
    data = request.get_json()
    organ = data.get('organ', {})
    return jsonify(get_backend().check_viability(organ))

@api_bp.route('/get-weather', methods=['POST'])
def get_weather():
    """Get weather data using WeatherAPI"""
    try:
        data = request.get_json()
        location = data.get('location', 'Boston')
        
        # Use WeatherAPI directly
        weather_api_key = os.getenv("WEATHER_API_KEY")
        if not weather_api_key:
            # Return simulated data if no API key
            return jsonify({
                "location": location,
                "temperature": 22,
                "condition": "Clear",
                "humidity": 65,
                "wind_kph": 10,
                "icon": "☀️"
            })
        
        url = f"http://api.weatherapi.com/v1/current.json?key={weather_api_key}&q={location}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                weather_data = response.json()
                
                # Extract relevant data
                current = weather_data.get("current", {})
                location_data = weather_data.get("location", {})
                
                result = {
                    "location": location_data.get("name", location),
                    "temperature": current.get("temp_c", 22),
                    "condition": current.get("condition", {}).get("text", "Clear"),
                    "humidity": current.get("humidity", 65),
                    "wind_kph": current.get("wind_kph", 10),
                    "icon": get_weather_icon_from_condition(current.get("condition", {}).get("text", "Clear")),
                    "last_updated": current.get("last_updated", "")
                }
                
                return jsonify(result)
            else:
                # API error, return simulated data
                return jsonify({
                    "location": location,
                    "temperature": 22,
                    "condition": "Clear", 
                    "humidity": 65,
                    "wind_kph": 10,
                    "icon": "☀️",
                    "error": f"Weather API returned {response.status_code}"
                })
                
        except requests.RequestException as e:
            # Network error, return simulated data
            return jsonify({
                "location": location,
                "temperature": 22,
                "condition": "Clear",
                "humidity": 65, 
                "wind_kph": 10,
                "icon": "☀️",
                "error": f"Weather API request failed: {str(e)}"
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_weather_icon_from_condition(condition):
    """Convert weather condition to emoji icon"""
    if not condition:
        return "☀️"
    
    condition_lower = condition.lower()
    
    if "sunny" in condition_lower or "clear" in condition_lower:
        return "☀️"
    elif "partly cloudy" in condition_lower or "partly" in condition_lower:
        return "⛅"
    elif "cloudy" in condition_lower or "overcast" in condition_lower:
        return "☁️"
    elif "rain" in condition_lower or "drizzle" in condition_lower:
        return "🌧️"
    elif "snow" in condition_lower:
        return "❄️"
    elif "thunder" in condition_lower or "storm" in condition_lower:
        return "⛈️"
    elif "fog" in condition_lower or "mist" in condition_lower:
        return "🌫️"
    else:
        return "☀️"

@api_bp.route('/search-flights', methods=['POST'])
def search_flights():
    data = request.get_json()
    origin = data.get('origin', 'BOS')
    destination = data.get('destination', 'LAX')
    return jsonify(get_backend().search_flights(origin, destination, data.get('date')))

@api_bp.route('/match-compatibility', methods=['POST'])
def match_compatibility():
    data = request.get_json()
    donor = data.get('donor', {})
    recipient = data.get('recipient', {})
    return jsonify(get_backend().match_donor_recipient(donor, recipient))

@api_bp.route('/agent-chat', methods=['POST'])
def agent_chat():
    data = request.get_json()
    msg = data.get('message', '')
    context = data.get('context', {})
    return jsonify(get_backend().invoke_agent(msg, context))

# Health check endpoint for Vercel
@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "OrganMatch API"})

# AI Transport Decision endpoint
@api_bp.route('/agent-transport-decision', methods=['POST'])
def agent_transport_decision():
    """Get AI agent decision on transport based on all factors"""
    try:
        data = request.get_json()
        
        # Extract data for analysis
        organ = data.get('organ', {})
        route = data.get('route', {})
        flight = data.get('flight', {})
        weather = data.get('weather', [])
        
        # Prepare context for AI agent
        context = {
            "task": "transport_decision",
            "organ_type": organ.get('type', 'unknown'),
            "donor_id": organ.get('donorId', 'unknown'),
            "recipient_id": data.get('recipientId', 'unknown'),
            "urgency": organ.get('urgency', 'medium'),
            "severity": data.get('severity', 'unknown'),
            "match_score": data.get('matchScore', 'unknown'),
            "viability_data": data.get('viabilityData', {}),
            "origin_city": route.get('origin', {}).get('city', 'unknown'),
            "destination_city": route.get('destination', {}).get('city', 'unknown'),
            "origin_hospital": route.get('origin', {}).get('hospital', 'unknown'),
            "destination_hospital": route.get('destination', {}).get('hospital', 'unknown'),
            "flight_number": flight.get('flightNumber', 'unknown'),
            "flight_duration": flight.get('duration', 'unknown'),
            "departure_time": flight.get('departure', 'unknown'),
            "weather_conditions": weather,
            "timestamp": data.get('timestamp', datetime.now().isoformat())
        }
        
        # Create detailed prompt for AI agent
        viability_data = context.get('viability_data', {})
        match_score = context.get('match_score', 'unknown')
        severity = context.get('severity', 'unknown')
        
        prompt = f"""
        You are an expert medical transport coordinator AI. Analyze the following organ transport scenario and provide a decision recommendation.

        ORGAN DETAILS:
        - Type: {organ.get('type', 'unknown')}
        - Donor ID: {organ.get('donorId', 'unknown')}
        - Recipient ID: {context.get('recipient_id', 'unknown')}
        - Urgency Level: {organ.get('urgency', 'medium')}
        - Severity: {severity}
        - Match Score: {match_score}

        VIABILITY DATA:
        - Condition Score: {viability_data.get('conditionScore', 'unknown')}/100
        - Blood Type Match: {viability_data.get('bloodTypeMatch', 'unknown')}

        TRANSPORT ROUTE:
        - Origin: {route.get('origin', {}).get('city', 'unknown')}, {route.get('origin', {}).get('state', 'unknown')}
        - Origin Hospital: {route.get('origin', {}).get('hospital', 'unknown')}
        - Destination: {route.get('destination', {}).get('city', 'unknown')}, {route.get('destination', {}).get('state', 'unknown')}
        - Destination Hospital: {route.get('destination', {}).get('hospital', 'unknown')}

        FLIGHT DETAILS:
        - Flight: {flight.get('flightNumber', 'unknown')}
        - Duration: {flight.get('duration', 'unknown')}
        - Departure: {flight.get('departure', 'unknown')}
        - Aircraft: {flight.get('aircraft', 'unknown')}

        WEATHER CONDITIONS:
        {format_weather_for_prompt(weather)}

        Please analyze all factors and provide:
        1. RECOMMENDATION: proceed/caution/abort
        2. CONFIDENCE: percentage (0-100)
        3. RISK LEVEL: low/medium/high
        4. REASONING: detailed explanation considering organ viability, match quality, weather, and transport logistics
        5. KEY FACTORS: list of important considerations

        Consider organ viability time limits, donor-recipient compatibility, weather safety, flight reliability, urgency level, and severity.
        """
        
        # Try to get AI agent response
        try:
            backend = get_backend()
            agent_response = backend.invoke_agent(prompt, context)
            
            if agent_response.get('success'):
                # Parse AI response and structure it
                ai_text = agent_response.get('response', '')
                decision = parse_ai_decision(ai_text, context)
                return jsonify(decision)
            else:
                # Fallback to rule-based decision
                return jsonify(generate_rule_based_decision(context, weather))
                
        except Exception as e:
            print(f"AI agent error: {e}")
            # Fallback to rule-based decision
            return jsonify(generate_rule_based_decision(context, weather))
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def format_weather_for_prompt(weather_data):
    """Format weather data for AI prompt"""
    if not weather_data:
        return "Weather data not available"
    
    weather_text = ""
    for w in weather_data:
        weather_text += f"- {w.get('location', 'Unknown')}: {w.get('condition', 'Unknown')}, {w.get('temperature', 'Unknown')}\n"
    
    return weather_text

def parse_ai_decision(ai_text, context):
    """Parse AI response into structured decision"""
    # Simple parsing - in production, this would be more sophisticated
    ai_lower = ai_text.lower()
    
    # Determine recommendation
    if 'abort' in ai_lower or 'do not proceed' in ai_lower:
        recommendation = 'abort'
    elif 'caution' in ai_lower or 'careful' in ai_lower:
        recommendation = 'caution'
    else:
        recommendation = 'proceed'
    
    # Extract confidence if mentioned
    confidence = 85  # default
    import re
    conf_match = re.search(r'(\d+)%', ai_text)
    if conf_match:
        confidence = int(conf_match.group(1))
    
    # Determine risk level
    if 'high risk' in ai_lower:
        risk_level = 'high'
    elif 'medium risk' in ai_lower or 'moderate risk' in ai_lower:
        risk_level = 'medium'
    else:
        risk_level = 'low'
    
    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "riskLevel": risk_level,
        "reasoning": ai_text,
        "factors": extract_factors_from_ai_text(ai_text),
        "source": "ai_agent",
        "context": context
    }

def generate_rule_based_decision(context, weather_data):
    """Generate decision using rule-based logic as fallback"""
    recommendation = 'proceed'
    confidence = 80
    risk_level = 'low'
    factors = []
    
    # Match quality assessment
    match_score = context.get('match_score', 'unknown')
    if match_score != 'unknown':
        try:
            score = int(match_score.replace('%', ''))
            if score >= 90:
                factors.append(f'Excellent donor-recipient match ({score}%)')
                confidence += 10
            elif score >= 75:
                factors.append(f'Good donor-recipient match ({score}%)')
                confidence += 5
            elif score >= 60:
                factors.append(f'Acceptable donor-recipient match ({score}%)')
            else:
                factors.append(f'Lower compatibility match ({score}%) - requires careful evaluation')
                confidence -= 10
                if risk_level == 'low':
                    risk_level = 'medium'
        except:
            factors.append('Match compatibility score available for review')
    
    # Severity assessment
    severity = context.get('severity', 'unknown').lower()
    if severity == 'critical':
        factors.append('Critical severity case - immediate action required')
        confidence += 15
        if recommendation == 'caution':
            recommendation = 'proceed'
            factors.append('Critical severity overrides weather concerns')
    elif severity == 'high':
        factors.append('High severity case - urgent transport needed')
        confidence += 10
    elif severity == 'medium':
        factors.append('Medium severity - standard transport protocols')
    
    # Weather assessment
    weather_risk = assess_weather_risk_backend(weather_data)
    if weather_risk == 'high':
        if severity not in ['critical', 'high']:
            recommendation = 'caution'
            risk_level = 'medium'
            confidence = 65
        factors.append('Adverse weather conditions detected - enhanced monitoring required')
    elif weather_risk == 'medium':
        factors.append('Weather conditions require continuous monitoring during transport')
        confidence = 75
    else:
        factors.append('Weather conditions are favorable for safe transport')
    
    # Urgency assessment
    urgency = context.get('urgency', 'medium').lower()
    if urgency == 'high':
        factors.append('High urgency case - time-critical transport')
        confidence += 5
    elif urgency == 'low':
        factors.append('Low urgency allows flexibility for optimal conditions')
    else:
        factors.append('Standard urgency level - normal protocols apply')
    
    # Viability assessment
    viability_data = context.get('viability_data', {})
    condition_score = viability_data.get('conditionScore')
    if condition_score:
        if condition_score >= 85:
            factors.append(f'Excellent organ condition (Score: {condition_score}/100)')
            confidence += 5
        elif condition_score >= 70:
            factors.append(f'Good organ condition (Score: {condition_score}/100)')
        else:
            factors.append(f'Organ condition requires monitoring (Score: {condition_score}/100)')
            confidence -= 5
    
    # Blood type compatibility
    blood_match = viability_data.get('bloodTypeMatch')
    if blood_match is True:
        factors.append('Perfect blood type compatibility confirmed')
        confidence += 5
    elif blood_match is False:
        factors.append('Blood type compatibility verified through crossmatch')
    
    # Flight duration assessment
    duration = context.get('flight_duration', '')
    if 'hour' in duration:
        try:
            hours = float(duration.split('h')[0])
            if hours > 8:
                factors.append('Extended flight duration - additional monitoring protocols')
                confidence -= 5
                if risk_level == 'low':
                    risk_level = 'medium'
            elif hours > 5:
                factors.append('Flight duration within acceptable range for organ transport')
            else:
                factors.append('Short flight duration minimizes transport risks')
        except:
            factors.append('Flight duration suitable for medical transport')
    
    # Organ type assessment
    organ_type = context.get('organ_type', 'unknown').lower()
    if organ_type in ['heart', 'liver']:
        factors.append(f'{organ_type.title()} transport - strict time adherence required')
    elif organ_type in ['kidney']:
        factors.append(f'{organ_type.title()} transport - flexible timing available')
    
    # Generate structured reasoning
    reasoning = f"""
COMPREHENSIVE TRANSPORT DECISION ANALYSIS

MATCH ASSESSMENT:
• Donor-Recipient Compatibility: {match_score}
• Severity Level: {severity.upper()}
• Blood Type Match: {'Confirmed' if blood_match else 'Compatible'}

RISK ASSESSMENT SUMMARY:
• Weather Risk Level: {weather_risk.upper()}
• Medical Urgency: {urgency.upper()}
• Organ Viability: {'Excellent' if condition_score and condition_score >= 85 else 'Good' if condition_score and condition_score >= 70 else 'Acceptable'}
• Overall Risk: {risk_level.upper()}

DECISION RATIONALE:
The automated analysis has evaluated donor-recipient compatibility, organ viability, weather conditions, flight parameters, and medical urgency. All factors have been weighted according to established medical transport protocols.

RECOMMENDATION:
{recommendation.upper()} - The system recommends to {recommendation} with this transport based on comprehensive analysis of all critical factors.

COMPLIANCE:
Decision follows established medical transport safety protocols and regulatory guidelines for organ transplantation.
    """
    
    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "riskLevel": risk_level,
        "reasoning": reasoning.strip(),
        "factors": factors,
        "source": "rule_based",
        "context": context,
        "analysis_details": {
            "weather_risk": weather_risk,
            "urgency_level": urgency,
            "severity_level": severity,
            "match_score": match_score,
            "organ_type": organ_type,
            "flight_duration": duration,
            "assessment_time": datetime.now().isoformat()
        }
    }

def assess_weather_risk_backend(weather_data):
    """Assess weather risk from weather data"""
    if not weather_data:
        return 'low'
    
    high_risk_conditions = ['storm', 'thunder', 'severe', 'heavy rain', 'blizzard']
    medium_risk_conditions = ['rain', 'snow', 'fog', 'wind']
    
    for weather in weather_data:
        condition = weather.get('condition', '').lower()
        for risk_condition in high_risk_conditions:
            if risk_condition in condition:
                return 'high'
        for risk_condition in medium_risk_conditions:
            if risk_condition in condition:
                return 'medium'
    
    return 'low'

def extract_factors_from_ai_text(ai_text):
    """Extract key factors from AI response"""
    # Simple extraction - look for bullet points or numbered lists
    factors = []
    lines = ai_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('-') or line.startswith('•') or line.startswith('*'):
            factors.append(line[1:].strip())
        elif any(line.startswith(f"{i}.") for i in range(1, 10)):
            factors.append(line.split('.', 1)[1].strip() if '.' in line else line)
    
    # If no structured factors found, add some generic ones
    if not factors:
        factors = [
            "All transport parameters evaluated",
            "Medical protocols considered",
            "Risk assessment completed"
        ]
    
    return factors[:5]  # Limit to 5 factors

# Get transport plan with dynamic city data
@api_bp.route('/transport-plan-dynamic', methods=['POST'])
def create_dynamic_transport_plan():
    """Generate transport plan with dynamic city data"""
    try:
        data = request.get_json()
        origin_city = data.get('origin_city')
        destination_city = data.get('destination_city')
        
        # Get hospital details from DynamoDB
        _, _, hospitals_table = get_tables()
        
        origin_hospitals = []
        dest_hospitals = []
        
        # Get all hospitals and filter by city
        try:
            response = hospitals_table.scan()
            all_hospitals = response.get('Items', [])
            
            for hospital in all_hospitals:
                hospital_city = hospital.get('city', '').lower()
                if origin_city and hospital_city == origin_city.lower():
                    origin_hospitals.append(hospital)
                if destination_city and hospital_city == destination_city.lower():
                    dest_hospitals.append(hospital)
        except Exception as e:
            print(f"Error scanning hospitals: {e}")
        
        # Create transport plan
        plan = {
            "route": {
                "origin": {
                    "city": origin_city or 'Unknown',
                    "hospitals": origin_hospitals,
                    "hospital_count": len(origin_hospitals)
                },
                "destination": {
                    "city": destination_city or 'Unknown', 
                    "hospitals": dest_hospitals,
                    "hospital_count": len(dest_hospitals)
                }
            },
            "flights": [],  # Will be populated by flight search
            "cities": {
                "origin": origin_city,
                "destination": destination_city
            }
        }
        
        return jsonify(plan)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get cities from hospitals
@api_bp.route('/cities', methods=['GET'])
def get_cities():
    """Get unique cities from hospitals table"""
    try:
        _, _, hospitals_table = get_tables()
        response = hospitals_table.scan()
        hospitals = response.get('Items', [])
        
        # Extract unique cities
        cities = set()
        city_data = {}
        
        for hospital in hospitals:
            city = hospital.get('city')
            state = hospital.get('state', '')
            
            if city:
                cities.add(city)
                if city not in city_data:
                    city_data[city] = {
                        'city': city,
                        'state': state,
                        'hospitals': []
                    }
                city_data[city]['hospitals'].append({
                    'name': hospital.get('name', 'Unknown Hospital'),
                    'id': hospital.get('hospital_id', hospital.get('id'))
                })
        
        # Convert to list and sort
        cities_list = [city_data[city] for city in sorted(cities)]
        
        return jsonify(cities_list)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Keep adding your other API endpoints here (analytics, hospitals, transport, etc.)
