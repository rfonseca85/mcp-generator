import httpx
import json
from typing import Dict, Any, List
import logging
import os
from openai import OpenAI

logger = logging.getLogger(__name__)

class MCPTester:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    async def test_mcp_server(self, mcp_config: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """Test an MCP server by sending a prompt and getting available tools"""
        
        results = {}
        
        for server_name, server_config in mcp_config.get("mcpServers", {}).items():
            try:
                result = await self._test_single_server(server_name, server_config, prompt)
                results[server_name] = result
            except Exception as e:
                logger.error(f"Error testing server {server_name}: {e}")
                results[server_name] = {"error": str(e)}
        
        return results
    
    async def _test_single_server(self, server_name: str, server_config: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """Test a single MCP server by executing the prompt"""
        
        url = server_config.get("url")
        if not url:
            raise ValueError(f"No URL provided for server {server_name}")
        
        async with httpx.AsyncClient() as client:
            # First, initialize the MCP server
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {},
                "id": "init-1"
            }
            
            init_response = await client.post(url, json=init_request)
            init_response.raise_for_status()
            init_data = init_response.json()
            
            if "error" in init_data and init_data["error"] is not None:
                raise Exception(f"Failed to initialize MCP server: {init_data['error']}")
            
            # Get available tools
            tools_request = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": "tools-1"
            }
            
            tools_response = await client.post(url, json=tools_request)
            tools_response.raise_for_status()
            tools_data = tools_response.json()
            
            if "error" in tools_data and tools_data["error"] is not None:
                raise Exception(f"Failed to get tools: {tools_data['error']}")
            
            available_tools = tools_data.get("result", {}).get("tools", [])
            
            if not available_tools:
                return {
                    "status": "success",
                    "available_tools": [],
                    "prompt": prompt,
                    "response": f"No tools available on {server_name}",
                    "tool_calls": []
                }
            
            # Use AI to determine which tools to call and how
            tool_execution_plan = await self._plan_tool_execution(prompt, available_tools)
            
            # Execute the planned tool calls
            tool_results = []
            for tool_call in tool_execution_plan:
                try:
                    result = await self._execute_tool_call(url, tool_call)
                    tool_results.append({
                        "tool": tool_call["name"],
                        "arguments": tool_call["arguments"],
                        "result": result,
                        "success": True
                    })
                except Exception as e:
                    tool_results.append({
                        "tool": tool_call["name"],
                        "arguments": tool_call["arguments"],
                        "error": str(e),
                        "success": False
                    })
            
            # Generate a final response based on the tool results
            final_response = await self._generate_final_response(prompt, available_tools, tool_results)
            
            return {
                "status": "success",
                "available_tools": available_tools,
                "prompt": prompt,
                "tool_calls": tool_results,
                "response": final_response
            }
    
    async def _plan_tool_execution(self, prompt: str, available_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use AI to plan which tools to execute based on the prompt"""
        
        # Generate detailed tool descriptions with parameter schemas
        tools_descriptions = []
        for tool in available_tools:
            tool_name = tool['name']
            tool_desc = tool.get('description', 'No description')
            input_schema = tool.get('inputSchema', {})
            properties = input_schema.get('properties', {})
            required = input_schema.get('required', [])
            
            param_details = []
            for param_name, param_info in properties.items():
                param_type = param_info.get('type', 'string')
                param_desc = param_info.get('description', 'No description')
                is_required = param_name in required
                req_indicator = " (required)" if is_required else " (optional)"
                param_details.append(f"    - {param_name} ({param_type}){req_indicator}: {param_desc}")
            
            param_section = "\n".join(param_details) if param_details else "    No parameters"
            tools_descriptions.append(f"- {tool_name}: {tool_desc}\n  Parameters:\n{param_section}")
        
        tools_description = "\n\n".join(tools_descriptions)
        
        system_prompt = f"""You are an AI assistant that helps execute user prompts using available MCP tools.

Available tools:
{tools_description}

Based on the user's prompt, determine which tools to call and with what arguments.

IMPORTANT: Use the exact parameter names as specified in the tool definitions above. Parameter names are case-sensitive.

If the user asks about available tools, don't call any tools, just return an empty array.
If the user wants to perform actions, determine the appropriate tools and arguments.

Respond with a JSON array of tool calls in this format:
[
  {{
    "name": "tool_name",
    "arguments": {{
      "exact_param_name": "value1",
      "another_param_name": "value2"
    }}
  }}
]

If no tools should be called, return an empty array: []"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            tool_plan_text = response.choices[0].message.content.strip()
            
            # Try to parse the JSON response
            if tool_plan_text.startswith("```json"):
                tool_plan_text = tool_plan_text[7:]
            if tool_plan_text.endswith("```"):
                tool_plan_text = tool_plan_text[:-3]
            
            tool_plan = json.loads(tool_plan_text.strip())
            
            # Validate that the planned tools exist
            available_tool_names = [tool["name"] for tool in available_tools]
            valid_tool_plan = []
            
            for tool_call in tool_plan:
                if tool_call.get("name") in available_tool_names:
                    valid_tool_plan.append(tool_call)
                else:
                    logger.warning(f"Tool {tool_call.get('name')} not found in available tools")
            
            return valid_tool_plan
            
        except Exception as e:
            logger.error(f"Error planning tool execution: {e}")
            return []
    
    async def _execute_tool_call(self, server_url: str, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool call on the MCP server using JSON-RPC"""
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_call["name"],
                "arguments": tool_call.get("arguments", {})
            },
            "id": f"call-{tool_call['name']}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(server_url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result and result["error"] is not None:
                raise Exception(f"Tool call failed: {result['error']}")
            
            return result.get("result", {})
    
    async def _generate_final_response(self, prompt: str, available_tools: List[Dict[str, Any]], tool_results: List[Dict[str, Any]]) -> str:
        """Generate a final response based on the prompt and tool execution results"""
        
        if not tool_results:
            # If no tools were executed, just list available tools
            tools_list = "\n".join([
                f"- **{tool['name']}**: {tool.get('description', 'No description')}"
                for tool in available_tools
            ])
            return f"Available tools:\n{tools_list}\n\nTo use a tool, specify it in your prompt (e.g., 'Use tool_name to do something')."
        
        # Summarize tool execution results
        success_count = sum(1 for result in tool_results if result.get("success", False))
        total_count = len(tool_results)
        
        response_parts = [f"Executed {success_count}/{total_count} tool calls successfully:"]
        
        for i, result in enumerate(tool_results, 1):
            if result.get("success", False):
                response_parts.append(f"\n{i}. ✅ **{result['tool']}**: {result.get('result', {}).get('result', 'Success')}")
            else:
                response_parts.append(f"\n{i}. ❌ **{result['tool']}**: {result.get('error', 'Unknown error')}")
        
        return "".join(response_parts)

    async def call_tool(self, server_url: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool on an MCP server"""
        
        call_url = f"{server_url}/call"
        
        payload = {
            "tool_name": tool_name,
            "arguments": arguments
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(call_url, json=payload)
            response.raise_for_status()
            return response.json()