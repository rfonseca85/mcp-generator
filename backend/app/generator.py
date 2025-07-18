import json
import zipfile
import io
from typing import Dict, Any, List, Optional
from openai import OpenAI
import os
from .templates import get_mcp_templates

class MCPGenerator:
    def __init__(self):
        self.client = None  # Will be initialized with config
        self.templates = get_mcp_templates()
    
    def _get_openai_client(self, config = None):
        """Get OpenAI client with configured or environment API key"""
        api_key = None
        if config:
            # Handle both dict and Pydantic model
            if hasattr(config, 'openai_api_key'):
                api_key = getattr(config, 'openai_api_key', None)
            elif isinstance(config, dict) and config.get("openai_api_key"):
                api_key = config["openai_api_key"]
        
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if api_key:
            return OpenAI(api_key=api_key)
        return None
    
    async def generate_mcp_project(self, api_spec: str, system_prompt: str, base_url: Optional[str] = None, selected_tools: Optional[List[str]] = None, config: Optional[Dict[str, Any]] = None) -> bytes:
        api_data = await self._parse_api_spec(api_spec)
        tools = await self._generate_tools_from_api(api_data, selected_tools, config)
        
        project_files = await self._generate_project_files(
            api_data, tools, system_prompt, base_url, config
        )
        
        return self._create_zip_file(project_files)
    
    async def _parse_api_spec(self, api_spec: str) -> Dict[str, Any]:
        try:
            return json.loads(api_spec)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in API specification")
    
    async def _generate_tools_from_api(self, api_data: Dict[str, Any], selected_tools: Optional[List[str]] = None, config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        tools = []
        
        if "paths" not in api_data:
            return tools
            
        for path, methods in api_data["paths"].items():
            for method, operation in methods.items():
                tool_id = f"{method}_{path}"
                
                # Skip if selected_tools is provided and this tool is not selected
                if selected_tools is not None and tool_id not in selected_tools:
                    continue
                    
                tool = await self._create_tool_from_operation(path, method, operation, api_data, config)
                if tool:
                    tools.append(tool)
        
        return tools
    
    def _resolve_schema_ref(self, ref: str, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a $ref reference to its actual schema definition"""
        if not ref.startswith("#/"):
            return {}
        
        parts = ref[2:].split("/")  # Remove #/ prefix
        current = api_data
        
        for part in parts:
            if part in current:
                current = current[part]
            else:
                return {}
        
        return current if isinstance(current, dict) else {}
    
    def _flatten_schema(self, schema: Dict[str, Any], api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten a schema by resolving all $ref references and extracting properties"""
        if "$ref" in schema:
            resolved = self._resolve_schema_ref(schema["$ref"], api_data)
            return self._flatten_schema(resolved, api_data)
        
        flattened = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        if "properties" in schema:
            flattened["properties"].update(schema["properties"])
        
        if "required" in schema:
            flattened["required"].extend(schema["required"])
        
        # Handle allOf, oneOf, anyOf
        for keyword in ["allOf", "oneOf", "anyOf"]:
            if keyword in schema:
                for subschema in schema[keyword]:
                    sub_flattened = self._flatten_schema(subschema, api_data)
                    flattened["properties"].update(sub_flattened.get("properties", {}))
                    flattened["required"].extend(sub_flattened.get("required", []))
        
        return flattened
    
    async def _create_tool_from_operation(self, path: str, method: str, operation: Dict[str, Any], api_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Generate cleaner tool names
        clean_name = self._generate_clean_tool_name(path, method, operation)
        operation_id = operation.get("operationId", clean_name)
        description = operation.get("description", operation.get("summary", f"{method.upper()} {path}"))
        
        # Start with empty parameters schema
        parameters_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # Handle path parameters - preserve original parameter names
        if "parameters" in operation:
            for param in operation["parameters"]:
                param_name = param["name"]  # Keep original parameter name exactly as in API spec
                param_schema = param.get("schema", {"type": "string"})
                parameters_schema["properties"][param_name] = param_schema
                
                if param.get("required", False):
                    parameters_schema["required"].append(param_name)
        
        # Handle request body with proper schema resolution
        if "requestBody" in operation:
            request_body = operation["requestBody"]
            if "content" in request_body:
                # Try application/json first, then fall back to the first available content type
                content_types = ["application/json", "application/x-www-form-urlencoded"]
                schema = None
                
                for content_type in content_types:
                    if content_type in request_body["content"]:
                        schema = request_body["content"][content_type].get("schema", {})
                        break
                
                if not schema and request_body["content"]:
                    # Use the first available content type
                    first_content = list(request_body["content"].values())[0]
                    schema = first_content.get("schema", {})
                
                if schema:
                    # Flatten and resolve the schema - this preserves original parameter names
                    flattened_schema = self._flatten_schema(schema, api_data)
                    parameters_schema["properties"].update(flattened_schema.get("properties", {}))
                    parameters_schema["required"].extend(flattened_schema.get("required", []))
        
        # Use AI to enhance the tool description and add parameter descriptions
        enhanced_tool = await self._enhance_tool_with_ai(
            operation_id, description, parameters_schema, path, method, operation, config
        )
        
        # Return MCP-compliant tool format
        return {
            "name": clean_name,  # Use clean name for tool identifier
            "description": enhanced_tool["description"],
            "inputSchema": enhanced_tool["parameters"],  # Use inputSchema instead of parameters
            # Additional metadata for handler generation
            "_method": method.upper(),
            "_path": path,
            "_original_name": operation_id
        }
    
    def _generate_clean_tool_name(self, path: str, method: str, operation: Dict[str, Any]) -> str:
        """Generate a clean, concise tool name from API operation"""
        
        # Try to use operationId if it's clean and concise
        operation_id = operation.get("operationId", "")
        if operation_id and len(operation_id) <= 25 and self._is_valid_python_identifier(operation_id):
            return operation_id.lower().replace(" ", "_")
        
        # Extract meaningful parts from path
        path_parts = [part for part in path.split('/') if part and not part.startswith('{')]
        
        # Clean path parts to be valid Python identifiers
        cleaned_parts = []
        for part in path_parts:
            # Replace hyphens and other invalid characters with underscores
            cleaned_part = self._sanitize_identifier(part)
            if cleaned_part:
                cleaned_parts.append(cleaned_part)
        
        # Get verb from method
        method_lower = method.lower()
        
        # Generate name based on method and path
        if method_lower == "get":
            if len(cleaned_parts) == 0:
                return "list_items"
            elif len(cleaned_parts) == 1:
                return f"get_{cleaned_parts[0]}"
            else:
                # For nested paths like /users/{id}/posts, create "get_user_posts"
                return f"get_{'_'.join(cleaned_parts[:2])}"
        
        elif method_lower == "post":
            if len(cleaned_parts) == 0:
                return "create_item"
            elif len(cleaned_parts) == 1:
                singular = self._make_singular(cleaned_parts[0])
                return f"create_{singular}"
            else:
                return f"create_{'_'.join(cleaned_parts[:2])}"
        
        elif method_lower == "put":
            if len(cleaned_parts) == 0:
                return "update_item"
            elif len(cleaned_parts) == 1:
                singular = self._make_singular(cleaned_parts[0])
                return f"update_{singular}"
            else:
                return f"update_{'_'.join(cleaned_parts[:2])}"
        
        elif method_lower == "patch":
            if len(cleaned_parts) == 0:
                return "modify_item"
            elif len(cleaned_parts) == 1:
                singular = self._make_singular(cleaned_parts[0])
                return f"modify_{singular}"
            else:
                return f"modify_{'_'.join(cleaned_parts[:2])}"
        
        elif method_lower == "delete":
            if len(cleaned_parts) == 0:
                return "delete_item"
            elif len(cleaned_parts) == 1:
                singular = self._make_singular(cleaned_parts[0])
                return f"delete_{singular}"
            else:
                return f"delete_{'_'.join(cleaned_parts[:2])}"
        
        # Fallback to original logic but cleaned up
        clean_path = self._sanitize_identifier(path.replace('/', '_').replace('{', '').replace('}', '').strip('_'))
        result = f"{method_lower}_{clean_path}"[:30].rstrip('_')
        
        # Ensure the result is a valid Python identifier
        return self._sanitize_identifier(result) or "generated_tool"
    
    def _sanitize_identifier(self, name: str) -> str:
        """Convert a string to a valid Python identifier"""
        import re
        
        # Replace invalid characters with underscores
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        
        # Ensure it doesn't start with a number
        if name and name[0].isdigit():
            name = f"tool_{name}"
        
        # Remove consecutive underscores
        name = re.sub(r'_+', '_', name)
        
        # Remove leading/trailing underscores
        name = name.strip('_')
        
        # Ensure it's not empty and not a Python keyword
        if not name or name in ['def', 'class', 'if', 'for', 'while', 'import', 'from', 'return', 'yield', 'try', 'except', 'finally', 'with', 'as', 'pass', 'break', 'continue', 'global', 'nonlocal', 'lambda', 'and', 'or', 'not', 'in', 'is', 'true', 'false', 'none']:
            name = f"tool_{name}" if name else "generated_tool"
        
        return name.lower()
    
    def _is_valid_python_identifier(self, name: str) -> bool:
        """Check if a string is a valid Python identifier"""
        import re
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name)) and not name.lower() in ['def', 'class', 'if', 'for', 'while', 'import', 'from', 'return', 'yield', 'try', 'except', 'finally', 'with', 'as', 'pass', 'break', 'continue', 'global', 'nonlocal', 'lambda', 'and', 'or', 'not', 'in', 'is', 'true', 'false', 'none']
    
    def _snake_to_camel(self, snake_str: str) -> str:
        """Convert snake_case to camelCase"""
        components = snake_str.split('_')
        return components[0] + ''.join(x.capitalize() for x in components[1:])
    
    def _camel_to_snake(self, camel_str: str) -> str:
        """Convert camelCase to snake_case"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _make_singular(self, word: str) -> str:
        """Simple singularization for common English words"""
        if word.endswith('s') and len(word) > 1:
            # Handle some common irregular plurals
            irregulars = {
                'children': 'child',
                'people': 'person',
                'men': 'man',
                'women': 'woman',
                'feet': 'foot',
                'teeth': 'tooth',
                'mice': 'mouse',
                'geese': 'goose'
            }
            
            if word in irregulars:
                return irregulars[word]
            
            # Simple rules for regular plurals
            if word.endswith('ies') and len(word) > 3:
                return word[:-3] + 'y'
            elif word.endswith('es') and len(word) > 2:
                if word.endswith(('ches', 'shes', 'xes', 'zes')):
                    return word[:-2]
                else:
                    return word[:-1]
            else:
                return word[:-1]
        
        return word
    
    async def _enhance_tool_with_ai(self, operation_id: str, description: str, parameters_schema: Dict[str, Any], path: str, method: str, operation: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Use AI to enhance tool description and add parameter descriptions"""
        
        # Create a comprehensive prompt for the AI
        prompt = f"""
You are an expert at creating MCP (Model Context Protocol) tool definitions from OpenAPI specifications.

Given this API operation:
- Operation ID: {operation_id}
- Path: {method.upper()} {path}
- Description: {description}
- Parameters Schema: {json.dumps(parameters_schema, indent=2)}
- Full Operation: {json.dumps(operation, indent=2)}

Please enhance this tool definition by:
1. Creating a clear, helpful description that explains what the tool does and when to use it
2. Adding helpful descriptions for each parameter
3. Ensuring the parameter schema is complete and usable

Respond with a JSON object containing:
{{
  "description": "Enhanced description of what this tool does",
  "parameters": {{
    "type": "object",
    "properties": {{
      "param_name": {{
        "type": "string",
        "description": "Clear description of this parameter"
      }}
    }},
    "required": ["required_param_names"]
  }}
}}

Make sure all required parameters are clearly marked and have good descriptions.
"""

        try:
            client = self._get_openai_client(config)
            if not client:
                # Fallback to original if no API key available
                return {
                    "description": description,
                    "parameters": parameters_schema
                }
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at creating clear, useful API tool definitions. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Clean up the response
            if ai_response.startswith("```json"):
                ai_response = ai_response[7:]
            if ai_response.endswith("```"):
                ai_response = ai_response[:-3]
            
            enhanced = json.loads(ai_response.strip())
            
            # Validate and merge with original schema
            if "description" in enhanced and "parameters" in enhanced:
                # Ensure we keep all original properties but enhance descriptions
                final_parameters = parameters_schema.copy()
                
                if "properties" in enhanced["parameters"]:
                    for param_name, param_def in enhanced["parameters"]["properties"].items():
                        if param_name in final_parameters["properties"]:
                            # Keep original type and name but add AI-generated description
                            if "description" in param_def:
                                final_parameters["properties"][param_name]["description"] = param_def["description"]
                        else:
                            # AI might have converted camelCase to snake_case - try to match
                            # Look for the original parameter name that might match this converted one
                            original_param = None
                            for orig_name in final_parameters["properties"].keys():
                                # Check if this could be a converted version of the original parameter
                                if (orig_name.lower().replace('_', '') == param_name.lower().replace('_', '') or
                                    self._snake_to_camel(param_name) == orig_name or
                                    self._camel_to_snake(orig_name) == param_name):
                                    original_param = orig_name
                                    break
                            
                            if original_param and "description" in param_def:
                                final_parameters["properties"][original_param]["description"] = param_def["description"]
                
                # Keep original required fields exactly as they are
                # Don't trust AI-generated required fields as they might have converted names
                if "required" in parameters_schema:
                    final_parameters["required"] = parameters_schema["required"]
                
                return {
                    "description": enhanced["description"],
                    "parameters": final_parameters
                }
        
        except Exception as e:
            print(f"AI enhancement failed for {operation_id}: {e}")
            # Fall back to original description and schema
            pass
        
        # Fallback to original if AI enhancement fails
        return {
            "description": description,
            "parameters": parameters_schema
        }
    
    async def _generate_project_files(self, api_data: Dict[str, Any], tools: List[Dict[str, Any]], system_prompt: str, base_url: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        api_info = api_data.get("info", {})
        # Use provided base_url or extract from API spec
        if base_url is None:
            base_url = self._extract_base_url(api_data)
        
        # Get configuration values with defaults
        # Handle both dict and Pydantic model
        def get_config_value(key, default):
            if not config:
                return default
            if hasattr(config, key):
                return getattr(config, key, default)
            elif isinstance(config, dict):
                return config.get(key, default)
            return default
        
        mcp_name = get_config_value("mcp_name", api_info.get("title", "Generated MCP Server"))
        description = get_config_value("description", api_info.get("description", "MCP Server generated from API spec"))
        protocol_types = get_config_value("protocol_types", ["stdio"])
        version = get_config_value("version", "1.0.0")
        author = get_config_value("author", "")
        
        files = {}
        
        # Convert JSON booleans to Python booleans for the template
        tools_python = self._convert_json_to_python(tools)
        
        # Generate files based on protocol types
        if len(protocol_types) == 1:
            # Single protocol - use specific templates
            protocol_type = protocol_types[0]
            if protocol_type == "sse":
                files["main.py"] = self.templates["main_sse_py"].format(
                    title=mcp_name,
                    description=description
                )
                files["sse_server.py"] = self.templates["sse_server_py"].format(
                    tools_json=tools_python
                )
                files["requirements.txt"] = self.templates["requirements_sse_txt"]
                files["README.md"] = self.templates["readme_sse_md"].format(
                    title=mcp_name,
                    description=description
                )
            else:
                # stdio or http
                files["main.py"] = self.templates["main_py"].format(
                    title=mcp_name,
                    description=description
                )
                files["mcp_server.py"] = self.templates["mcp_server_py"].format(
                    tools_json=tools_python
                )
                files["requirements.txt"] = self.templates["requirements_txt"]
                files["README.md"] = self.templates["readme_md"].format(
                    title=mcp_name,
                    description=description
                )
        else:
            # Multiple protocols - use multi-protocol template
            files["main.py"] = self.templates["main_multi_py"].format(
                title=mcp_name,
                description=description,
                supported_protocols=json.dumps(protocol_types)
            )
            
            # Include servers for all selected protocols
            if "stdio" in protocol_types or "http" in protocol_types:
                files["mcp_server.py"] = self.templates["mcp_server_py"].format(
                    tools_json=tools_python
                )
            
            if "sse" in protocol_types:
                files["sse_server.py"] = self.templates["sse_server_py"].format(
                    tools_json=tools_python
                )
            
            files["requirements.txt"] = self.templates["requirements_multi_txt"]
            
            # Generate multi-protocol README
            protocol_list = ", ".join(p.upper() for p in protocol_types)
            protocol_details = self._generate_protocol_details(protocol_types)
            usage_examples = self._generate_usage_examples(protocol_types)
            api_endpoints = self._generate_api_endpoints(protocol_types)
            protocol_technical_details = self._generate_protocol_technical_details(protocol_types)
            
            files["README.md"] = self.templates["readme_multi_md"].format(
                title=mcp_name,
                description=description,
                protocol_list=protocol_list,
                protocol_details=protocol_details,
                usage_examples=usage_examples,
                api_endpoints=api_endpoints,
                protocol_technical_details=protocol_technical_details,
                server_name=mcp_name.lower().replace(" ", "-")
            )
        
        # Common files for all protocols
        files["handlers.py"] = await self._generate_handlers(tools, base_url)
        files["Dockerfile"] = self.templates["dockerfile"]
        files["run.sh"] = self.templates["run_sh"]
        files["prompt.txt"] = system_prompt
        
        # Add metadata file with configuration
        metadata = {
            "name": mcp_name,
            "description": description,
            "version": version,
            "author": author,
            "protocols": protocol_types,
            "base_url": base_url,
            "generated_at": "2024-01-01T00:00:00Z",  # You might want to use actual timestamp
            "tools_count": len(tools)
        }
        files["metadata.json"] = json.dumps(metadata, indent=2)
        
        return files
    
    def _generate_protocol_details(self, protocol_types: List[str]) -> str:
        """Generate protocol details section for README"""
        details = []
        for protocol in protocol_types:
            if protocol == "stdio":
                details.append("- **STDIO**: Direct input/output communication for Cursor and Claude Desktop integration")
            elif protocol == "http":
                details.append("- **HTTP**: RESTful API for web integration and testing")
            elif protocol == "sse":
                details.append("- **SSE**: Server-Sent Events for real-time bidirectional communication")
        return "\n".join(details)
    
    def _generate_usage_examples(self, protocol_types: List[str]) -> str:
        """Generate usage examples section for README"""
        examples = []
        for protocol in protocol_types:
            if protocol == "stdio":
                examples.append("#### STDIO (Default)\n```bash\npython main.py --stdio\n```\n*For Cursor/Claude Desktop integration*")
            elif protocol == "http":
                examples.append("#### HTTP Server\n```bash\npython main.py --http\n```\n*Starts HTTP server on http://localhost:8080*")
            elif protocol == "sse":
                examples.append("#### SSE Server\n```bash\npython main.py --sse\n```\n*Starts SSE server on http://localhost:8080/sse*")
        return "\n\n".join(examples)
    
    def _generate_api_endpoints(self, protocol_types: List[str]) -> str:
        """Generate API endpoints section for README"""
        endpoints = []
        if "http" in protocol_types or "sse" in protocol_types:
            endpoints.append("- `GET /` - Health check and server info")
            endpoints.append("- `POST /` - JSON-RPC MCP requests")
        if "sse" in protocol_types:
            endpoints.append("- `GET /sse` - Server-Sent Events stream")
        if "stdio" in protocol_types:
            endpoints.append("- **STDIO**: Direct JSON-RPC communication via stdin/stdout")
        return "\n".join(endpoints) if endpoints else "No HTTP endpoints (STDIO only)"
    
    def _generate_protocol_technical_details(self, protocol_types: List[str]) -> str:
        """Generate technical details section for README"""
        details = []
        for protocol in protocol_types:
            if protocol == "stdio":
                details.append("### STDIO Protocol\n- JSON-RPC 2.0 over stdin/stdout\n- Non-blocking async I/O\n- Error handling with proper JSON-RPC error responses")
            elif protocol == "http":
                details.append("### HTTP Protocol\n- RESTful JSON-RPC API\n- CORS enabled for web integration\n- FastAPI with automatic OpenAPI documentation")
            elif protocol == "sse":
                details.append("### SSE Protocol\n- Server-Sent Events for real-time communication\n- Heartbeat mechanism every 30 seconds\n- Automatic reconnection support\n- JSON message format over SSE")
        return "\n\n".join(details)
    
    async def _generate_handlers(self, tools: List[Dict[str, Any]], base_url: str) -> str:
        handlers_code = []
        
        for tool in tools:
            handler_code = self._generate_handler_function(tool, base_url)
            handlers_code.append(handler_code)
        
        return self.templates["handlers_py"].format(
            base_url=base_url,
            handlers="\n\n".join(handlers_code)
        )
    
    def _generate_handler_function(self, tool: Dict[str, Any], base_url: str) -> str:
        properties = tool["inputSchema"].get("properties", {})
        required_params = tool["inputSchema"].get("required", [])
        
        # Generate parameter validation
        validation_code = []
        for param in required_params:
            validation_code.append(f'    if "{param}" not in args or args["{param}"] is None:')
            validation_code.append(f'        return {{"error": "Missing required parameter: {param}"}}')
        
        validation_block = "\n".join(validation_code) if validation_code else "    # No required parameters to validate"
        
        # Generate parameter extraction with proper type conversion
        param_extraction = []
        for param_name, param_def in properties.items():
            param_type = param_def.get("type", "string")
            default_value = param_def.get("default")
            
            if param_name in required_params:
                # Required parameters with type conversion
                if param_type == "integer":
                    param_extraction.append(f'    {param_name} = int(args["{param_name}"]) if args["{param_name}"] not in ["", None] else None')
                elif param_type == "number":
                    param_extraction.append(f'    {param_name} = float(args["{param_name}"]) if args["{param_name}"] not in ["", None] else None')
                elif param_type == "boolean":
                    param_extraction.append(f'    {param_name} = bool(args["{param_name}"]) if args["{param_name}"] not in ["", None] else None')
                else:
                    param_extraction.append(f'    {param_name} = args["{param_name}"] if args["{param_name}"] != "" else None')
            else:
                # Optional parameters with defaults and type conversion
                # Properly format default values based on type
                if default_value is None:
                    formatted_default = "None"
                elif isinstance(default_value, str):
                    formatted_default = json.dumps(default_value)
                elif isinstance(default_value, (int, float)):
                    formatted_default = str(default_value)
                elif isinstance(default_value, bool):
                    formatted_default = "True" if default_value else "False"
                else:
                    formatted_default = json.dumps(str(default_value))
                
                if param_type == "integer":
                    param_extraction.append(f'    {param_name}_raw = args.get("{param_name}", {formatted_default})')
                    param_extraction.append(f'    try:')
                    param_extraction.append(f'        {param_name} = int({param_name}_raw) if {param_name}_raw not in ["", None] else {formatted_default}')
                    param_extraction.append(f'    except (ValueError, TypeError):')
                    param_extraction.append(f'        {param_name} = {formatted_default}')
                elif param_type == "number":
                    param_extraction.append(f'    {param_name}_raw = args.get("{param_name}", {formatted_default})')
                    param_extraction.append(f'    try:')
                    param_extraction.append(f'        {param_name} = float({param_name}_raw) if {param_name}_raw not in ["", None] else {formatted_default}')
                    param_extraction.append(f'    except (ValueError, TypeError):')
                    param_extraction.append(f'        {param_name} = {formatted_default}')
                elif param_type == "boolean":
                    param_extraction.append(f'    {param_name}_raw = args.get("{param_name}", {formatted_default})')
                    param_extraction.append(f'    if {param_name}_raw in ["", None, "false", "False", False, 0]:')
                    param_extraction.append(f'        {param_name} = False')
                    param_extraction.append(f'    elif {param_name}_raw in ["true", "True", True, 1]:')
                    param_extraction.append(f'        {param_name} = True')
                    param_extraction.append(f'    else:')
                    param_extraction.append(f'        {param_name} = {formatted_default}')
                else:
                    param_extraction.append(f'    {param_name} = args.get("{param_name}", {formatted_default})')
        
        extraction_block = "\n".join(param_extraction) if param_extraction else "    # No parameters to extract"
        
        # Build request payload
        if tool["_method"] in ["POST", "PUT", "PATCH"]:
            payload_items = [f'"{param}": {param}' for param in properties.keys()]
            payload_dict = "{" + ", ".join(payload_items) + "}"
            request_code = f'''
    # Build request payload
    payload = {payload_dict}
    # Remove None values
    payload = {{k: v for k, v in payload.items() if v is not None}}
    
    # Make HTTP request
    async with httpx.AsyncClient() as client:
        response = await client.{tool["_method"].lower()}(
            url=f"{base_url}{tool["_path"]}",
            json=payload,
            headers={{"Content-Type": "application/json"}}
        )'''
        else:
            # For GET requests, use query parameters
            payload_items = [f'"{param}": {param}' for param in properties.keys()]
            payload_dict = "{" + ", ".join(payload_items) + "}"
            request_code = f'''
    # Build query parameters
    params = {payload_dict}
    # Remove None values
    params = {{k: v for k, v in params.items() if v is not None}}
    
    # Make HTTP request
    async with httpx.AsyncClient() as client:
        response = await client.{tool["_method"].lower()}(
            url=f"{base_url}{tool["_path"]}",
            params=params
        )'''
        
        return f'''async def {tool["name"]}(args: dict) -> dict:
    """
    {tool["description"]}
    
    Parameters:
{self._generate_param_docs(properties)}
    """
    import httpx
    
    # Validate required parameters
{validation_block}
    
    # Extract parameters
{extraction_block}
{request_code}
        
        # Handle response
        if response.status_code >= 400:
            try:
                error_detail = response.json()
                return {{"error": f"HTTP {{response.status_code}}: {{error_detail}}"}}
            except:
                return {{"error": f"HTTP {{response.status_code}}: {{response.text}}"}}
        
        try:
            return response.json()
        except:
            return {{"result": response.text}}'''
    
    def _generate_param_docs(self, properties: Dict[str, Any]) -> str:
        """Generate parameter documentation for the handler function"""
        docs = []
        for param_name, param_def in properties.items():
            param_type = param_def.get("type", "string")
            param_desc = param_def.get("description", "No description available")
            docs.append(f"    - {param_name} ({param_type}): {param_desc}")
        
        return "\n".join(docs) if docs else "    No parameters"
    
    def _convert_json_to_python(self, obj: Any) -> str:
        """Convert a JSON object to a Python string representation"""
        def convert_value(value):
            if isinstance(value, bool):
                return "True" if value else "False"
            elif isinstance(value, str):
                return repr(value)  # Uses proper escaping
            elif isinstance(value, (int, float)):
                return str(value)
            elif value is None:
                return "None"
            elif isinstance(value, list):
                items = [convert_value(item) for item in value]
                return "[" + ", ".join(items) + "]"
            elif isinstance(value, dict):
                items = []
                for k, v in value.items():
                    key_str = repr(k)
                    val_str = convert_value(v)
                    items.append(f"{key_str}: {val_str}")
                return "{" + ", ".join(items) + "}"
            else:
                return repr(str(value))
        
        return convert_value(obj)
    
    def _extract_base_url(self, api_data: Dict[str, Any]) -> str:
        if "servers" in api_data and api_data["servers"]:
            return api_data["servers"][0]["url"]
        return "http://localhost:8080"
    
    def _create_zip_file(self, files: Dict[str, str]) -> bytes:
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, content in files.items():
                zip_file.writestr(f"mcp_project/{filename}", content)
        
        zip_buffer.seek(0)
        return zip_buffer.read()