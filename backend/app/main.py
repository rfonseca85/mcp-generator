from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import os
from dotenv import load_dotenv

from .generator import MCPGenerator
from .tester import MCPTester

load_dotenv()

app = FastAPI(title="MCP Generator and Tester", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

generator = MCPGenerator()
tester = MCPTester()

class MCPConfig(BaseModel):
    openai_api_key: Optional[str] = None
    mcp_name: Optional[str] = None
    protocol_types: Optional[List[str]] = None
    description: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None

class GenerateRequest(BaseModel):
    api_spec: str
    system_prompt: str
    base_url: Optional[str] = None  # Optional base URL override
    selected_tools: Optional[List[str]] = None  # Optional list of selected tool IDs
    config: Optional[MCPConfig] = None

class TestRequest(BaseModel):
    mcp_config: Dict[str, Any]
    prompt: str

@app.get("/")
def root():
    return {"message": "MCP Generator and Tester API"}

@app.post("/generate")
async def generate_mcp(request: GenerateRequest):
    try:
        zip_bytes = await generator.generate_mcp_project(
            request.api_spec,
            request.system_prompt,
            request.base_url,
            request.selected_tools,
            request.config
        )
        return {"zip_data": zip_bytes.hex()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test")
async def test_mcp(request: TestRequest):
    try:
        result = await tester.test_mcp_server(
            request.mcp_config,
            request.prompt
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)