import boto3

gateway_id = "organmatch-gateway"
region = "us-east-1"
account = boto3.client("sts").get_caller_identity()["Account"]

# Correct client for registering Lambda tools
client = boto3.client("bedrock-agent-gateway", region_name=region)

tools = [
    ("viability-tool", "lambda_viability_tool"),
    ("matcher-tool", "lambda_matcher_tool"),
    ("flight-tool", "lambda_flight_tool"),
    ("weather-tool", "lambda_weather_tool"),
]

for name, func in tools:
    arn = f"arn:aws:lambda:{region}:{account}:function:{func}"
    resp = client.create_tool(
        gatewayIdentifier=gateway_id,   # parameter name is gatewayIdentifier, not gatewayId
        name=name,
        description=f"OrganMatch {name.replace('-', ' ')}",
        lambdaFunction={ "arn": arn }
    )
    print(f"✅ Registered {name}: {resp['tool']['arn']}")
