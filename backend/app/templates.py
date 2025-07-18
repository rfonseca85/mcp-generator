def get_mcp_templates():
    return {
        "main_py": '''#!/usr/bin/env python3
"""
{title}
{description}
"""
import asyncio
import logging
import sys
import json
from mcp_server import MCPServer

logging.basicConfig(level=logging.ERROR)  # Reduce logging for stdio transport
logger = logging.getLogger(__name__)

async def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        # HTTP mode for testing
        server = MCPServer()
        await server.start()
    else:
        # Stdio mode for Cursor/Claude Desktop
        print("Starting STDIO MCP Server for Cursor/Claude Desktop integration", file=sys.stderr)
        await stdio_main()

async def stdio_main():
    """Handle MCP protocol over stdio for Cursor integration"""
    server = MCPServer()
    
    loop = asyncio.get_event_loop()
    
    while True:
        try:
            # Read line from stdin in a non-blocking way
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
                
            line = line.strip()
            if not line:
                continue
                
            request = json.loads(line)
            response = await server.handle_mcp_request(request)
            
            if response:
                print(json.dumps(response), flush=True)
            
        except json.JSONDecodeError as e:
            error_response = {{
                "jsonrpc": "2.0",
                "error": {{"code": -32700, "message": f"Parse error: {{str(e)}}"}},
                "id": None
            }}
            print(json.dumps(error_response), flush=True)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Stdio error: {{e}}")
            error_response = {{
                "jsonrpc": "2.0", 
                "error": {{"code": -32603, "message": f"Internal error: {{str(e)}}"}},
                "id": None
            }}
            print(json.dumps(error_response), flush=True)

if __name__ == "__main__":
    asyncio.run(main())
''',
        
        "mcp_server_py": '''import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import handlers

logger = logging.getLogger(__name__)

class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class MCPServer:
    def __init__(self):
        self.app = FastAPI(title="MCP Server")
        self.tools = {tools_json}
        self.initialized = False
        self.server_info = {{
            "name": "Generated MCP Server",
            "version": "1.0.0"
        }}
        self.setup_routes()
        self.setup_middleware()
    
    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        @self.app.get("/")
        def root():
            return {{"message": "MCP Server is running"}}
        
        @self.app.post("/")
        async def handle_jsonrpc(request: JsonRpcRequest):
            """Handle MCP JSON-RPC requests"""
            try:
                if request.method == "initialize":
                    return await self._handle_initialize(request)
                elif request.method == "tools/list":
                    if not self.initialized:
                        return JsonRpcResponse(
                            id=request.id,
                            error={{"code": -32002, "message": "Server not initialized"}}
                        )
                    return JsonRpcResponse(
                        id=request.id,
                        result={{"tools": self.tools}}
                    )
                elif request.method == "tools/call":
                    if not self.initialized:
                        return JsonRpcResponse(
                            id=request.id,
                            error={{"code": -32002, "message": "Server not initialized"}}
                        )
                    return await self._handle_tool_call(request)
                elif request.method == "ping":
                    return JsonRpcResponse(
                        id=request.id,
                        result={{}}
                    )
                else:
                    return JsonRpcResponse(
                        id=request.id,
                        error={{"code": -32601, "message": "Method not found"}}
                    )
            except Exception as e:
                logger.error(f"JSON-RPC error: {{e}}")
                return JsonRpcResponse(
                    id=request.id if hasattr(request, 'id') else None,
                    error={{"code": -32603, "message": "Internal error"}}
                )
        
        # Legacy REST endpoints for testing
        @self.app.get("/mcp")
        def get_tools():
            return {{"tools": self.tools}}
        
        @self.app.post("/mcp/call")
        async def call_tool(request: ToolCallRequest):
            if request.tool_name not in [tool["name"] for tool in self.tools]:
                raise HTTPException(status_code=404, detail="Tool not found")
            
            handler = getattr(handlers, request.tool_name, None)
            if not handler:
                raise HTTPException(status_code=500, detail="Handler not implemented")
            
            try:
                result = await handler(request.arguments)
                return {{"result": result}}
            except Exception as e:
                logger.error(f"Error calling tool {{request.tool_name}}: {{e}}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _handle_initialize(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """Handle MCP initialize request"""
        try:
            client_info = request.params or {{}}
            self.initialized = True
            
            return JsonRpcResponse(
                id=request.id,
                result={{
                    "protocolVersion": "2025-03-26",
                    "capabilities": {{
                        "tools": {{
                            "listChanged": False
                        }}
                    }},
                    "serverInfo": self.server_info
                }}
            )
        except Exception as e:
            return JsonRpcResponse(
                id=request.id,
                error={{"code": -32603, "message": f"Initialize failed: {{str(e)}}"}}
            )
    
    async def _handle_tool_call(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """Handle tools/call request"""
        try:
            if not request.params:
                return JsonRpcResponse(
                    id=request.id,
                    error={{"code": -32602, "message": "Missing parameters"}}
                )
            
            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {{}})
            
            if tool_name not in [tool["name"] for tool in self.tools]:
                return JsonRpcResponse(
                    id=request.id,
                    error={{"code": -32602, "message": "Tool not found"}}
                )
            
            handler = getattr(handlers, tool_name, None)
            if not handler:
                return JsonRpcResponse(
                    id=request.id,
                    error={{"code": -32603, "message": "Handler not implemented"}}
                )
            
            result = await handler(arguments)
            
            # Format result according to MCP spec
            if isinstance(result, dict) and "error" in result:
                # Tool execution error
                return JsonRpcResponse(
                    id=request.id,
                    result={{
                        "content": [{{
                            "type": "text",
                            "text": str(result.get("error", "Unknown error"))
                        }}],
                        "isError": True
                    }}
                )
            else:
                # Successful result
                content_text = json.dumps(result) if not isinstance(result, str) else result
                return JsonRpcResponse(
                    id=request.id,
                    result={{
                        "content": [{{
                            "type": "text",
                            "text": content_text
                        }}],
                        "isError": False
                    }}
                )
        except Exception as e:
            logger.error(f"Error calling tool: {{e}}")
            return JsonRpcResponse(
                id=request.id,
                error={{"code": -32603, "message": str(e)}}
            )
    
    async def handle_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests for stdio transport"""
        method = request.get("method")
        params = request.get("params", {{}})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                self.initialized = True
                return {{
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {{
                        "protocolVersion": "2025-03-26",
                        "capabilities": {{
                            "tools": {{
                                "listChanged": False
                            }}
                        }},
                        "serverInfo": self.server_info
                    }}
                }}
            elif method == "notifications/initialized":
                # Client confirmation that initialization is complete
                return None  # No response needed for notifications
            elif method == "tools/list":
                if not self.initialized:
                    return {{
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {{"code": -32002, "message": "Server not initialized"}}
                    }}
                return {{
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {{"tools": self.tools}}
                }}
            elif method == "tools/call":
                if not self.initialized:
                    return {{
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {{"code": -32002, "message": "Server not initialized"}}
                    }}
                
                tool_name = params.get("name")
                arguments = params.get("arguments", {{}})
                
                if tool_name not in [tool["name"] for tool in self.tools]:
                    return {{
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {{"code": -32602, "message": "Tool not found"}}
                    }}
                
                handler = getattr(handlers, tool_name, None)
                if not handler:
                    return {{
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {{"code": -32603, "message": "Handler not implemented"}}
                    }}
                
                try:
                    result = await handler(arguments)
                    
                    # Format result according to MCP spec
                    if isinstance(result, dict) and "error" in result:
                        # Tool execution error
                        return {{
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {{
                                "content": [{{
                                    "type": "text",
                                    "text": str(result.get("error", "Unknown error"))
                                }}],
                                "isError": True
                            }}
                        }}
                    else:
                        # Successful result
                        content_text = json.dumps(result) if not isinstance(result, str) else result
                        return {{
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {{
                                "content": [{{
                                    "type": "text",
                                    "text": content_text
                                }}],
                                "isError": False
                            }}
                        }}
                except Exception as e:
                    return {{
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {{"code": -32603, "message": str(e)}}
                    }}
            elif method == "ping":
                return {{
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {{}}
                }}
            else:
                return {{
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {{"code": -32601, "message": "Method not found"}}
                }}
        except Exception as e:
            return {{
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {{"code": -32603, "message": "Internal error"}}
            }}
    
    async def start(self):
        import uvicorn
        config = uvicorn.Config(self.app, host="0.0.0.0", port=8080)
        server = uvicorn.Server(config)
        await server.serve()

class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
''',
        
        "handlers_py": '''import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

BASE_URL = "{base_url}"

{handlers}
''',
        
        "requirements_txt": '''fastapi==0.115.5
uvicorn==0.33.0
httpx==0.28.1
pydantic==2.10.3
python-multipart==0.0.20
''',
        
        "dockerfile": '''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "main.py"]
''',
        
        "run_sh": '''#!/bin/bash
set -e

echo "Starting MCP Server..."

if [ "$1" == "docker" ]; then
    echo "Building Docker image..."
    docker build -t mcp-server .
    echo "Running Docker container..."
    docker run -p 8080:8080 mcp-server
elif [ "$1" == "http" ]; then
    echo "Setting up Python virtual environment..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "✅ Virtual environment created"
    else
        echo "✅ Virtual environment already exists"
    fi
    
    echo "Activating virtual environment..."
    source ./venv/bin/activate
    
    echo "Installing dependencies..."
    pip install -r requirements.txt
    
    echo "Starting HTTP server on port 8080..."
    python main.py --http
else
    echo "Setting up Python virtual environment..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "✅ Virtual environment created"
    else
        echo "✅ Virtual environment already exists"
    fi
    
    echo "Activating virtual environment..."
    source ./venv/bin/activate
    
    echo "Installing dependencies..."
    pip install -r requirements.txt
    
    echo "Starting MCP server (stdio mode for Cursor/Claude Desktop)..."
    python main.py
fi
''',
        
        "readme_md": '''# {title}

{description}

## Generated MCP Server

This is a Model Context Protocol (MCP) server generated from an API specification.

## Running the Server

### Option 1: For Cursor/Claude Desktop (Recommended)
```bash
chmod +x run.sh
./run.sh
```
*This starts the MCP server in stdio mode for proper Cursor integration.*

### Option 2: HTTP Mode (for testing)
```bash
chmod +x run.sh
./run.sh http
```
*This starts an HTTP server on port 8080 for REST API testing.*

### Option 3: Docker
```bash
chmod +x run.sh
./run.sh docker
```

### Option 4: Manual Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source ./venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run in stdio mode (default)
python main.py

# Or run in HTTP mode
python main.py --http
```

## Configuration

### Cursor Integration
Add to your `.cursor/config.json`:
```json
{{
  "mcpServers": {{
    "generated-mcp": {{
      "command": "python",
      "args": ["main.py"],
      "cwd": "/path/to/your/mcp_project"
    }}
  }}
}}
```

### Claude Desktop Integration
Add to your `claude_desktop_config.json`:
```json
{{
  "mcpServers": {{
    "generated-mcp": {{
      "command": "python",
      "args": ["main.py"],
      "cwd": "/path/to/your/mcp_project"
    }}
  }}
}}
```

### HTTP Transport (for testing)
If you want to use HTTP transport instead:
```json
{{
  "mcpServers": {{
    "generated-mcp": {{
      "url": "http://localhost:8080",
      "transport": "http"
    }}
  }}
}}
```

## API Endpoints

- `GET /` - Health check
- `GET /mcp` - List available tools
- `POST /mcp/call` - Call a tool

## System Prompt

The AI system prompt for this server is stored in `prompt.txt`.

## Development

This server was generated using the MCP Generator tool. To modify the behavior:

1. Edit the handlers in `handlers.py`
2. Update the system prompt in `prompt.txt`
3. Restart the server

## Technical Notes

- Uses async/await for proper asyncio integration
- Built with FastAPI for high performance
- Supports CORS for web integration
- Generated handlers make HTTP calls to your specified base URL
''',
        
        "sse_server_py": '''import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import handlers

logger = logging.getLogger(__name__)

class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SSE MCP Server")
    yield
    logger.info("Shutting down SSE MCP Server")

class SSEMCPServer:
    def __init__(self):
        self.app = FastAPI(title="SSE MCP Server", lifespan=lifespan)
        self.tools = {tools_json}
        self.initialized = False
        self.server_info = {{
            "name": "Generated SSE MCP Server",
            "version": "1.0.0"
        }}
        self.setup_routes()
        self.setup_middleware()
    
    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        @self.app.get("/")
        def root():
            return {{"message": "SSE MCP Server is running", "protocol": "sse"}}
        
        @self.app.get("/sse")
        async def sse_endpoint(request: Request):
            """Server-Sent Events endpoint for MCP communication"""
            return StreamingResponse(
                self.sse_stream(request),
                media_type="text/event-stream",
                headers={{
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control"
                }}
            )
        
        @self.app.post("/")
        async def handle_jsonrpc(request: JsonRpcRequest):
            """Handle MCP JSON-RPC requests via POST"""
            try:
                response = await self._handle_mcp_request(request.dict())
                return response
            except Exception as e:
                logger.error(f"JSON-RPC error: {{e}}")
                return JsonRpcResponse(
                    id=request.id if hasattr(request, 'id') else None,
                    error={{"code": -32603, "message": "Internal error"}}
                )
    
    async def sse_stream(self, request: Request) -> AsyncGenerator[str, None]:
        """Stream SSE messages for MCP communication"""
        try:
            # Send initial connection message
            yield f"data: {{json.dumps({{'type': 'connection', 'status': 'connected'}})}}\\n\\n"
            
            # Keep connection alive and wait for client disconnect
            while True:
                if await request.is_disconnected():
                    break
                
                # Send periodic heartbeat
                yield f"data: {{json.dumps({{'type': 'heartbeat', 'timestamp': asyncio.get_event_loop().time()}})}}\\n\\n"
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
        except Exception as e:
            logger.error(f"SSE stream error: {{e}}")
            yield f"data: {{json.dumps({{'type': 'error', 'message': str(e)}})}}\\n\\n"
    
    async def _handle_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests"""
        method = request.get("method")
        params = request.get("params", {{}})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                self.initialized = True
                return {{
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {{
                        "protocolVersion": "2025-03-26",
                        "capabilities": {{
                            "tools": {{
                                "listChanged": False
                            }}
                        }},
                        "serverInfo": self.server_info
                    }}
                }}
            elif method == "notifications/initialized":
                return None  # No response needed for notifications
            elif method == "tools/list":
                if not self.initialized:
                    return {{
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {{"code": -32002, "message": "Server not initialized"}}
                    }}
                return {{
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {{"tools": self.tools}}
                }}
            elif method == "tools/call":
                if not self.initialized:
                    return {{
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {{"code": -32002, "message": "Server not initialized"}}
                    }}
                
                tool_name = params.get("name")
                arguments = params.get("arguments", {{}})
                
                if tool_name not in [tool["name"] for tool in self.tools]:
                    return {{
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {{"code": -32602, "message": "Tool not found"}}
                    }}
                
                handler = getattr(handlers, tool_name, None)
                if not handler:
                    return {{
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {{"code": -32603, "message": "Handler not implemented"}}
                    }}
                
                try:
                    result = await handler(arguments)
                    
                    # Format result according to MCP spec
                    if isinstance(result, dict) and "error" in result:
                        return {{
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {{
                                "content": [{{
                                    "type": "text",
                                    "text": str(result.get("error", "Unknown error"))
                                }}],
                                "isError": True
                            }}
                        }}
                    else:
                        content_text = json.dumps(result) if not isinstance(result, str) else result
                        return {{
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {{
                                "content": [{{
                                    "type": "text",
                                    "text": content_text
                                }}],
                                "isError": False
                            }}
                        }}
                except Exception as e:
                    return {{
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {{"code": -32603, "message": str(e)}}
                    }}
            elif method == "ping":
                return {{
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {{}}
                }}
            else:
                return {{
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {{"code": -32601, "message": "Method not found"}}
                }}
        except Exception as e:
            return {{
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {{"code": -32603, "message": "Internal error"}}
            }}
    
    async def start(self):
        import uvicorn
        config = uvicorn.Config(self.app, host="0.0.0.0", port=8080)
        server = uvicorn.Server(config)
        await server.serve()
''',

        "main_sse_py": '''#!/usr/bin/env python3
"""
{title}
{description}
"""
import asyncio
import logging
import sys
from sse_server import SSEMCPServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        print("Error: SSE protocol does not support stdio mode", file=sys.stderr)
        print("Use: python main.py (for SSE server)", file=sys.stderr)
        sys.exit(1)
    else:
        # SSE mode
        print("Starting SSE MCP Server on http://localhost:8080", file=sys.stderr)
        print("SSE endpoint: http://localhost:8080/sse", file=sys.stderr)
        server = SSEMCPServer()
        await server.start()

if __name__ == "__main__":
    asyncio.run(main())
''',

        "requirements_sse_txt": '''fastapi==0.115.5
uvicorn==0.33.0
httpx==0.28.1
pydantic==2.10.3
python-multipart==0.0.20
sse-starlette==2.2.0
''',

        "main_multi_py": '''#!/usr/bin/env python3
"""
{title}
{description}
"""
import asyncio
import logging
import sys
import json
from typing import List

# Import available servers based on what's included
try:
    from mcp_server import MCPServer
    HAS_STDIO_HTTP = True
except ImportError:
    HAS_STDIO_HTTP = False

try:
    from sse_server import SSEMCPServer
    HAS_SSE = True
except ImportError:
    HAS_SSE = False

logging.basicConfig(level=logging.ERROR)  # Reduce logging for stdio transport
logger = logging.getLogger(__name__)

SUPPORTED_PROTOCOLS = {supported_protocols}

async def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg == "--help" or arg == "-h":
            print_help()
            return
            
        elif arg == "--sse" and "sse" in SUPPORTED_PROTOCOLS:
            if not HAS_SSE:
                print("Error: SSE server not available in this build", file=sys.stderr)
                sys.exit(1)
            print("Starting SSE MCP Server on http://localhost:8080", file=sys.stderr)
            print("SSE endpoint: http://localhost:8080/sse", file=sys.stderr)
            server = SSEMCPServer()
            await server.start()
            
        elif arg == "--http" and "http" in SUPPORTED_PROTOCOLS:
            if not HAS_STDIO_HTTP:
                print("Error: HTTP server not available in this build", file=sys.stderr)
                sys.exit(1)
            print("Starting HTTP MCP Server on http://localhost:8080", file=sys.stderr)
            server = MCPServer()
            await server.start()
            
        elif arg == "--stdio" and "stdio" in SUPPORTED_PROTOCOLS:
            if not HAS_STDIO_HTTP:
                print("Error: STDIO server not available in this build", file=sys.stderr)
                sys.exit(1)
            print("Starting STDIO MCP Server for Cursor/Claude Desktop integration", file=sys.stderr)
            await stdio_main()
            
        else:
            print(f"Error: Unknown or unsupported protocol: {{arg}}", file=sys.stderr)
            print_help()
            sys.exit(1)
    else:
        # Default behavior - start the primary protocol
        if "stdio" in SUPPORTED_PROTOCOLS and HAS_STDIO_HTTP:
            print("Starting STDIO MCP Server (default)", file=sys.stderr)
            await stdio_main()
        elif "http" in SUPPORTED_PROTOCOLS and HAS_STDIO_HTTP:
            print("Starting HTTP MCP Server (default)", file=sys.stderr)
            server = MCPServer()
            await server.start()
        elif "sse" in SUPPORTED_PROTOCOLS and HAS_SSE:
            print("Starting SSE MCP Server (default)", file=sys.stderr)
            server = SSEMCPServer()
            await server.start()
        else:
            print("Error: No supported protocols available", file=sys.stderr)
            sys.exit(1)

async def stdio_main():
    """Handle MCP protocol over stdio for Cursor integration"""
    server = MCPServer()
    
    loop = asyncio.get_event_loop()
    
    while True:
        try:
            # Read line from stdin in a non-blocking way
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
                
            line = line.strip()
            if not line:
                continue
                
            request = json.loads(line)
            response = await server.handle_mcp_request(request)
            
            if response:
                print(json.dumps(response), flush=True)
            
        except json.JSONDecodeError as e:
            error_response = {{
                "jsonrpc": "2.0",
                "error": {{"code": -32700, "message": f"Parse error: {{str(e)}}"}},
                "id": None
            }}
            print(json.dumps(error_response), flush=True)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Stdio error: {{e}}")
            error_response = {{
                "jsonrpc": "2.0", 
                "error": {{"code": -32603, "message": f"Internal error: {{str(e)}}"}},
                "id": None
            }}
            print(json.dumps(error_response), flush=True)

def print_help():
    """Print usage help"""
    print("Usage: python main.py [PROTOCOL]")
    print()
    print("Supported protocols in this build:")
    for protocol in SUPPORTED_PROTOCOLS:
        if protocol == "stdio":
            print("  --stdio    Start STDIO server (for Cursor/Claude Desktop)")
        elif protocol == "http":
            print("  --http     Start HTTP server on port 8080")
        elif protocol == "sse":
            print("  --sse      Start SSE server on port 8080")
    print()
    print("  --help, -h Show this help message")
    print()
    print("If no protocol is specified, the primary protocol will be used.")

if __name__ == "__main__":
    asyncio.run(main())
''',

        "requirements_multi_txt": '''fastapi==0.115.5
uvicorn==0.33.0
httpx==0.28.1
pydantic==2.10.3
python-multipart==0.0.20
sse-starlette==2.2.0
''',

        "readme_multi_md": '''# {title}

{description}

## Multi-Protocol MCP Server

This MCP server supports multiple communication protocols: {protocol_list}.

## Supported Protocols

{protocol_details}

## Running the Server

### Quick Start
```bash
chmod +x run.sh
./run.sh
```

### Protocol-Specific Usage

{usage_examples}

### Docker
```bash
chmod +x run.sh
./run.sh docker
```

### Manual Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source ./venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run with specific protocol
python main.py --stdio    # For Cursor/Claude Desktop
python main.py --http     # For HTTP API testing
python main.py --sse      # For real-time SSE communication
```

## Configuration

### Cursor/Claude Desktop Integration
Add to your configuration file:

```json
{{
  "mcpServers": {{
    "{server_name}": {{
      "command": "python",
      "args": ["main.py", "--stdio"],
      "cwd": "/path/to/your/mcp_project"
    }}
  }}
}}
```

### HTTP/SSE Integration
For web integration:
```json
{{
  "mcpServers": {{
    "{server_name}": {{
      "url": "http://localhost:8080",
      "transport": "http"
    }}
  }}
}}
```

## API Endpoints

{api_endpoints}

## System Prompt

The AI system prompt for this server is stored in `prompt.txt`.

## Technical Notes

- Multi-protocol support in single codebase
- Protocol selection via command line arguments
- Graceful fallback if protocols are not available
- Built with FastAPI for high performance
- Generated handlers make HTTP calls to your specified base URL

## Protocol Details

{protocol_technical_details}
''',

        "readme_sse_md": '''# {title}

{description}

## Generated SSE MCP Server

This is a Model Context Protocol (MCP) server with Server-Sent Events (SSE) support generated from an API specification.

## Running the Server

### SSE Mode (Default)
```bash
chmod +x run.sh
./run.sh
```
*This starts the SSE MCP server on port 8080.*

### Endpoints
- **HTTP POST**: `http://localhost:8080` - JSON-RPC requests
- **SSE Stream**: `http://localhost:8080/sse` - Server-Sent Events
- **Health Check**: `http://localhost:8080` - Server status

### Testing the SSE Connection
```bash
curl -N -H "Accept: text/event-stream" http://localhost:8080/sse
```

### Docker
```bash
chmod +x run.sh
./run.sh docker
```

### Manual Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source ./venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run SSE server
python main.py
```

## Configuration

### For SSE Integration
Configure your client to connect to:
```
SSE Endpoint: http://localhost:8080/sse
JSON-RPC Endpoint: http://localhost:8080
```

### Example SSE Client Connection
```javascript
const eventSource = new EventSource('http://localhost:8080/sse');
eventSource.onmessage = function(event) {{
  const data = JSON.parse(event.data);
  console.log('Received:', data);
}};
```

### Claude Desktop Integration (HTTP Mode)
Add to your `claude_desktop_config.json`:
```json
{{
  "mcpServers": {{
    "generated-sse-mcp": {{
      "url": "http://localhost:8080",
      "transport": "http"
    }}
  }}
}}
```

## API Endpoints

- `GET /` - Health check and server info
- `GET /sse` - Server-Sent Events stream
- `POST /` - JSON-RPC MCP requests

## System Prompt

The AI system prompt for this server is stored in `prompt.txt`.

## Technical Notes

- Built with FastAPI and SSE support
- Supports real-time bidirectional communication
- CORS enabled for web integration
- Heartbeat mechanism for connection monitoring
- Generated handlers make HTTP calls to your specified base URL

## SSE Protocol Details

- Connection endpoint: `/sse`
- Message format: JSON over SSE
- Heartbeat interval: 30 seconds
- Automatic reconnection supported
'''
    }