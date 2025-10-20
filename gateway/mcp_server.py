#!/usr/bin/env python3
"""
MCP Server for OrganMatch Gateway Tools
Bridges AWS Bedrock AgentCore Gateway tools to MCP protocol
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List

import boto3

# Simple MCP protocol implementation
class SimpleMCPServer:
    def __init__(self):
        self.tools = {}
        
    async def handle_request(self, request):
        """Handle MCP requests"""
        method = request.get("method")
        
        if method == "tools/list":
            return await self.list_tools()
        elif method == "tools/call":
            params = request.get("params", {})
            return await self.call_tool(params.get("name"), params.get("arguments", {}))
        else:
            return {"error": f"Unknown method: {method}"}
    
    async def list_tools(self):
        """List available tools"""
        await self.load_gateway_tools()
        
        tools = []
        for tool_name, tool_spec in self.tools.items():
            tools.append({
                "name": tool_name,
                "description": tool_spec.get("description", ""),
                "inputSchema": tool_spec.get("inputSchema", {})
            })
        
        return {"tools": tools}
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]):
        """Execute a tool"""
        if name not in self.tools:
            return {"error": f"Tool {name} not found"}
        
        try:
            target_id = self.tools[name].get("targetId")
            if not target_id:
                return {"error": f"Target not found for tool {name}"}
            
            # Invoke the gateway target
            # Try different service names based on boto3 version
            service_names = ["bedrock-agentcore-control", "bedrock-agent", "bedrock"]
            agentcore = None
            
            for service_name in service_names:
                try:
                    agentcore = boto3.client(service_name, region_name=REGION)
                    if hasattr(agentcore, 'invoke_gateway_target') or hasattr(agentcore, 'invoke_target'):
                        break
                except Exception:
                    continue
            
            if not agentcore:
                raise Exception("Gateway service not available")
            
            try:
                if hasattr(agentcore, 'invoke_gateway_target'):
                    response = agentcore.invoke_gateway_target(
                        gatewayIdentifier=GATEWAY_ID,
                        targetId=target_id,
                        input=json.dumps(arguments)
                    )
                else:
                    response = agentcore.invoke_target(
                        gatewayIdentifier=GATEWAY_ID,
                        targetId=target_id,
                        input=json.dumps(arguments)
                    )
            except Exception as e:
                raise Exception(f"Failed to invoke gateway target: {e}")
            
            result = response.get("output", {})
            if isinstance(result, str):
                result = json.loads(result)
            
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
            
        except Exception as e:
            return {"error": f"Error executing {name}: {str(e)}"}
    
    async def load_gateway_tools(self):
        """Load tool definitions from the gateway"""
        try:
            # Try different service names based on boto3 version
            service_names = ["bedrock-agentcore-control", "bedrock-agent", "bedrock"]
            agentcore = None
            
            for service_name in service_names:
                try:
                    agentcore = boto3.client(service_name, region_name=REGION)
                    if hasattr(agentcore, 'list_gateway_targets'):
                        break
                except Exception:
                    continue
            
            if not agentcore or not hasattr(agentcore, 'list_gateway_targets'):
                raise Exception("Gateway service not available in current boto3 version")
            
            targets = agentcore.list_gateway_targets(gatewayIdentifier=GATEWAY_ID)
            
            for target in targets.get("items", []):
                target_id = target["targetId"]
                target_name = target["name"]
                
                try:
                    details = agentcore.get_gateway_target(
                        gatewayIdentifier=GATEWAY_ID,
                        targetId=target_id
                    )
                    
                    tools_schema = (
                        details.get("targetConfiguration", {})
                               .get("mcp", {})
                               .get("lambda", {})
                               .get("toolSchema", {})
                               .get("inlinePayload", [])
                    )
                    
                    if tools_schema:
                        for tool in tools_schema:
                            tool_name = tool.get("name")
                            if tool_name:
                                self.tools[tool_name] = {
                                    "description": tool.get("description", ""),
                                    "inputSchema": tool.get("inputSchema", {}),
                                    "outputSchema": tool.get("outputSchema", {}),
                                    "targetId": target_id
                                }
                
                except Exception as e:
                    print(f"Error loading target {target_name}: {e}", file=sys.stderr)
                    
        except Exception as e:
            print(f"Error loading gateway tools: {e}", file=sys.stderr)

# Configuration
REGION = os.getenv("AWS_REGION", "us-east-1")
GATEWAY_ID = os.getenv("GATEWAY_ID", "organmatch-gateway-lorsb6rxxr")

async def main():
    """Main entry point - simple JSON-RPC over stdio"""
    server = SimpleMCPServer()
    
    # Simple stdio JSON-RPC loop
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            request = json.loads(line.strip())
            response = await server.handle_request(request)
            
            # Send response
            print(json.dumps(response))
            sys.stdout.flush()
            
        except Exception as e:
            error_response = {"error": str(e)}
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())