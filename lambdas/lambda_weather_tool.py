import json
import urllib.request
import urllib.parse
import boto3, json, os


secret_name = "organmatch/weatherapi"
region = "us-east-1"

client = boto3.client("secretsmanager", region_name=region)
secret = client.get_secret_value(SecretId=secret_name)
secrets = json.loads(secret["SecretString"])

API_KEY = secrets["API_KEY"]



def lambda_handler(event, context):
    """
    Fetches current weather data for a given location using WeatherAPI.
    No external dependencies required (uses urllib).
    """

    # --- Parse the incoming request ---
    body = event.get("body")
    if isinstance(body, str):
        body = json.loads(body or "{}")
    elif body is None:
        body = {}

    location = body.get("location", "London")

    # --- Build and call the WeatherAPI URL ---
    query = urllib.parse.quote(location)
    url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={query}"

    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            data = json.loads(response.read().decode())

        # --- Extract relevant details ---
        weather = {
            "location": data["location"]["name"],
            "region": data["location"]["region"],
            "country": data["location"]["country"],
            "temp_c": data["current"]["temp_c"],
            "condition": data["current"]["condition"]["text"],
            "humidity": data["current"]["humidity"],
            "wind_kph": data["current"]["wind_kph"]
        }

        return {
            "statusCode": 200,
            "body": json.dumps(weather)
        }

    except Exception as e:
        # Catch connection, parsing, or API key errors
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }
