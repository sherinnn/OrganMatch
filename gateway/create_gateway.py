import os, boto3, json
from utils import get_or_create_cognito_pool, put_ssm_parameter, get_ssm_parameter

REGION = boto3.session.Session().region_name
gateway_client = boto3.client("bedrock-agentcore-control", region_name=REGION)

gateway_name = "organmatch-gateway"
print(f"Creating gateway in region {REGION} with name: {gateway_name}")

# 1️⃣ Fetch Cognito pool details (provisioned already in your AWS account)
cognito_config = get_or_create_cognito_pool(refresh_token=True)
auth_config = {
    "customJWTAuthorizer": {
        "allowedClients": [cognito_config["client_id"]],
        "discoveryUrl": cognito_config["discovery_url"],
    }
}

try:
    create_response = gateway_client.create_gateway(
        name=gateway_name,
        roleArn=get_ssm_parameter("/app/organmatch/agentcore/gateway_iam_role"),
        protocolType="MCP",
        authorizerType="CUSTOM_JWT",
        authorizerConfiguration=auth_config,
        description="OrganMatch AgentCore Gateway for Lambda-based tools",
    )

    gateway_id  = create_response["gatewayId"]
    gateway_url = create_response["gatewayUrl"]

    put_ssm_parameter("/app/organmatch/agentcore/gateway_id",  gateway_id)
    put_ssm_parameter("/app/organmatch/agentcore/gateway_url", gateway_url)
    put_ssm_parameter("/app/organmatch/agentcore/gateway_name", gateway_name)

    print(f"✅ Gateway created successfully → ID: {gateway_id}")
    print(f"🔗 MCP Endpoint: {gateway_url}")

except Exception:
    existing_gateway_id = get_ssm_parameter("/app/organmatch/agentcore/gateway_id")
    print(f"ℹ️ Gateway already exists (ID: {existing_gateway_id})")
