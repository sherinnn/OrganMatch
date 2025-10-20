import json, boto3

s3 = boto3.client("s3")
BUCKET_NAME = "organmatch-flight-data"
FILE_KEY = "mock_flights.json"

def lambda_handler(event, context):
    body = event.get("body")
    if isinstance(body, str):
        body = json.loads(body or "{}")
    elif body is None:
        body = {}

    from_city = body.get("from_city", "").upper()
    to_city = body.get("to_city", "").upper()

    try:
        # Read file from S3
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=FILE_KEY)
        data = json.loads(obj["Body"].read().decode("utf-8"))

        # Filter flights by route
        flights = [f for f in data if f["from"] == from_city and f["to"] == to_city]

        return {"statusCode": 200, "body": json.dumps({"flights": flights})}

    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}
