import boto3, os, json, uuid, random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from backend.utils import simulate_weather_data, simulate_viability_check, simulate_flight_search, simulate_donor_matching


load_dotenv()

# --- AWS Configuration ---
REGION = os.getenv("REGION")
GATEWAY_ID = os.getenv("GATEWAY_ID")
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
AGENT_ID = os.getenv("AGENT_ID")
AGENT_ALIAS_ID = os.getenv("AGENT_ALIAS_ID")

# --- Initialize AWS Clients (global, accessible to class) ---
try:
    bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)
    bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)
    try:
        agentcore_client = boto3.client("bedrock-agentcore-control", region_name=REGION)
        AGENTCORE_AVAILABLE = True
    except Exception:
        agentcore_client = None
        AGENTCORE_AVAILABLE = False
except Exception as e:
    print(f"⚠️ AWS initialization failed: {e}")
    bedrock_runtime = None
    bedrock_agent_runtime = None
    agentcore_client = None
    AGENTCORE_AVAILABLE = False




# DynamoDB connection
dynamodb = boto3.resource("dynamodb", region_name=REGION)

# Tables (replace names if different)
donors_table = dynamodb.Table("donors")
recipients_table = dynamodb.Table("recipients")
hospitals_table = dynamodb.Table("hospitals")



class OrganMatchBackend:
    """Backend logic for OrganMatch operations"""
    
    def __init__(self):
        self.bedrock_runtime = bedrock_runtime
        self.bedrock_agent_runtime = bedrock_agent_runtime
        self.agentcore_client = agentcore_client
        self.session_id = str(uuid.uuid4())
        
        # Load gateway target mappings
        self.gateway_targets = self._load_gateway_targets() if AGENTCORE_AVAILABLE else {}
    
    def _load_gateway_targets(self):
        """Load gateway target mappings for tool invocation"""
        
        if not self.agentcore_client:
            return {}
        
        try:
            targets = self.agentcore_client.list_gateway_targets(gatewayIdentifier=GATEWAY_ID)
            target_map = {}
            
            for target in targets.get("items", []):
                target_map[target["name"]] = target["targetId"]
            
            print(f"✅ Loaded {len(target_map)} gateway targets")
            return target_map
            
        except Exception as e:
            print(f"⚠️ Could not load gateway targets: {e}")
            return {}
    
    def invoke_agent(self, prompt, context=None):
        """Invoke the OrganMatch agent with context - tries AgentCore first, falls back to direct model"""
        
        # Try AgentCore agent first
        agent_result = self._try_agentcore_invoke(prompt, context)
        if agent_result["success"]:
            return agent_result
        
        # Fallback to direct model invocation
        return self._invoke_direct_model(prompt, context)
    
    def _try_agentcore_invoke(self, prompt, context=None):
        """Try to invoke the actual Bedrock agent"""
        
        try:
            # Prepare the input text
            if context:
                context_str = f"Context: {json.dumps(context, indent=2)}\n\n"
                input_text = f"{context_str}{prompt}"
            else:
                input_text = prompt
            
            # Invoke the agent
            response = self.bedrock_agent_runtime.invoke_agent(
                agentId=AGENT_ID,
                agentAliasId=AGENT_ALIAS_ID,
                sessionId=self.session_id,
                inputText=input_text,
                enableTrace=True
            )
            
            # Process the streaming response
            full_response = ""
            traces = []
            
            for event in response['completion']:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        text = chunk['bytes'].decode('utf-8')
                        full_response += text
                
                elif 'trace' in event:
                    traces.append(event['trace'])
            
            return {
                "success": True,
                "response": full_response,
                "method": "agentcore",
                "traces": len(traces)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "agentcore"
            }
    
    def _invoke_direct_model(self, prompt, context=None):
        """Fallback to direct model invocation"""
        
        system_prompt = """You are OrganMatch AI Assistant, a specialized medical logistics AI that helps hospitals and transplant coordinators manage organ transplantation workflows.

## Your Role & Capabilities:
You assist with organ viability assessment, donor-recipient matching, transport logistics, and system monitoring. You have access to real-time data and specialized medical tools.

## Response Format Guidelines:
- Structure your responses with clear headings using ## for main topics and ### for subtopics
- Use bullet points (-) for lists and important information
- Highlight key metrics, status indicators, and critical information
- Use **bold** for emphasis on important terms
- Keep responses concise but comprehensive
- Always prioritize patient safety and time-sensitive information

## Available Tools & Data:
- Organ viability assessment (time, temperature, condition scoring)
- Weather monitoring for transport safety
- Flight search and booking for urgent transport
- Donor-recipient compatibility matching
- Real-time system status and metrics

## Communication Style:
- Professional and medical-focused
- Clear, actionable recommendations
- Time-sensitive awareness (organs have limited viability windows)
- Structured information presentation
- Empathetic to the critical nature of organ transplantation

Always format your responses with proper structure, bullet points for key information, and clear sections for easy reading."""
        
        if context:
            context_str = f"\nContext: {json.dumps(context, indent=2)}"
            full_prompt = f"{system_prompt}{context_str}\n\nUser: {prompt}\n\nOrganMatch Agent:"
        else:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nOrganMatch Agent:"
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 800,
            "messages": [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ]
        })
        
        try:
            response = self.bedrock_runtime.invoke_model(
                modelId=MODEL_ID,
                body=body
            )
            
            response_body = json.loads(response['body'].read())
            return {
                "success": True,
                "response": response_body['content'][0]['text'],
                "method": "direct_model"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "direct_model"
            }
    
    def invoke_gateway_tool(self, tool_name, parameters):
        """Invoke a specific gateway tool via AgentCore"""
        
        if not self.agentcore_client or tool_name not in self.gateway_targets:
            return {"success": False, "error": f"Tool {tool_name} not available via gateway"}
        
        target_id = self.gateway_targets[tool_name]
        
        try:
            # Try different invoke methods based on SDK version
            invoke_methods = ["invoke_gateway_target", "invoke_target"]
            
            for method_name in invoke_methods:
                if hasattr(self.agentcore_client, method_name):
                    try:
                        method = getattr(self.agentcore_client, method_name)
                        response = method(
                            gatewayIdentifier=GATEWAY_ID,
                            targetId=target_id,
                            input=json.dumps(parameters)
                        )
                        
                        # Parse response
                        output = response.get('output', {})
                        if isinstance(output, str):
                            try:
                                output = json.loads(output)
                            except:
                                pass
                        
                        return {
                            "success": True,
                            "result": output,
                            "method": method_name
                        }
                        
                    except Exception as e:
                        continue
            
            return {"success": False, "error": "No compatible invoke method found"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_viability(self, organ_data):
        """Check organ viability - tries gateway first, falls back to simulation"""
        
        # Try gateway tool first
        if AGENTCORE_AVAILABLE and "viability-tool" in self.gateway_targets:
            gateway_params = {
                "organ_type": organ_data.get("type", "heart"),
                "time_of_death": organ_data.get("donation_time", datetime.now().isoformat()),
                "current_time": datetime.now().isoformat(),
                "temperature_c": organ_data.get("temperature", 4),
                "organ_condition_score": organ_data.get("condition_score", 85)
            }
            
            gateway_result = self.invoke_gateway_tool("viability-tool", gateway_params)
            if gateway_result["success"]:
                result = gateway_result["result"]
                result["method"] = "gateway"
                return result
        
        # Fallback to simulation
        return self._simulate_viability_check(organ_data)
    
    def _simulate_viability_check(self, organ_data):
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
    
    def get_weather(self, location, latitude=None, longitude=None):
        """Get weather data - tries gateway first, falls back to simulation"""
        
        # Try gateway tool first
        if AGENTCORE_AVAILABLE and "weather-tool" in self.gateway_targets:
            # Use provided coordinates or default ones for common cities
            coords = self._get_coordinates(location, latitude, longitude)
            
            gateway_params = {
                "latitude": coords["lat"],
                "longitude": coords["lon"]
            }
            
            gateway_result = self.invoke_gateway_tool("weather-tool", gateway_params)
            if gateway_result["success"]:
                result = gateway_result["result"]
                result["method"] = "gateway"
                result["location"] = location
                return result
        
        # Fallback to simulation
        return self._simulate_weather_data(location)
    
    def _get_coordinates(self, location, latitude=None, longitude=None):
        """Get coordinates for a location"""
        
        if latitude is not None and longitude is not None:
            return {"lat": latitude, "lon": longitude}
        
        # Common city coordinates
        city_coords = {
            "boston": {"lat": 42.3601, "lon": -71.0589},
            "new york": {"lat": 40.7128, "lon": -74.0060},
            "los angeles": {"lat": 34.0522, "lon": -118.2437},
            "chicago": {"lat": 41.8781, "lon": -87.6298},
            "miami": {"lat": 25.7617, "lon": -80.1918},
            "seattle": {"lat": 47.6062, "lon": -122.3321}
        }
        
        location_lower = location.lower()
        return city_coords.get(location_lower, {"lat": 42.3601, "lon": -71.0589})
    
    def _simulate_weather_data(self, location):
        """Simulate weather data"""
        
        weather_data = {
            "temperature_c": 15,
            "condition": "Clear",
            "wind_kph": 12,
            "visibility_km": 10,
            "humidity": 65,
            "transport_suitability": "Excellent",
            "location": location,
            "method": "simulation"
        }
        
        return weather_data
    
    def search_flights(self, origin, destination, date=None):
        """Search flights - tries gateway first, falls back to simulation"""
        
        # Try gateway tool first
        if AGENTCORE_AVAILABLE and "flight-tool" in self.gateway_targets:
            gateway_params = {
                "origin": origin,
                "destination": destination,
                "departure_date": date or datetime.now().strftime("%Y-%m-%d")
            }
            
            gateway_result = self.invoke_gateway_tool("flight-tool", gateway_params)
            if gateway_result["success"]:
                result = gateway_result["result"]
                result["method"] = "gateway"
                return result
        
        # Fallback to simulation
        return self._simulate_flight_search(origin, destination, date)
    
    def _simulate_flight_search(self, origin, destination, date=None):
        """Simulate flight search"""
        
        # Simulate flight data
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
    
    def match_donor_recipient(self, donor_data, recipient_data):
        """Match donor-recipient - tries gateway first, falls back to simulation"""
        
        # Try gateway tool first
        if AGENTCORE_AVAILABLE and "matcher-tool" in self.gateway_targets:
            gateway_params = {
                "donor_id": donor_data.get("id", "D123"),
                "recipient_id": recipient_data.get("id", "R456")
            }
            
            gateway_result = self.invoke_gateway_tool("matcher-tool", gateway_params)
            if gateway_result["success"]:
                result = gateway_result["result"]
                result["method"] = "gateway"
                return result
        
        # Fallback to simulation
        return self._simulate_donor_matching(donor_data, recipient_data)
    
    def _simulate_donor_matching(self, donor_data, recipient_data):
        """Simulate donor-recipient matching"""
        
        # Simple matching logic
        blood_match = donor_data.get("blood_type") == recipient_data.get("blood_type")
        
        # Simulate compatibility score
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
