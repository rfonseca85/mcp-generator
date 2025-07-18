const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface GenerateRequest {
  api_spec: string
  system_prompt: string
  base_url?: string
  selected_tools?: string[]
  config?: {
    openai_api_key?: string
    mcp_name?: string
    protocol_types?: ('stdio' | 'http' | 'sse')[]
    description?: string
    version?: string
    author?: string
  }
}

export interface TestRequest {
  mcp_config: Record<string, unknown>
  prompt: string
}

export interface GenerateResponse {
  zip_data: string
}

export interface TestResponse {
  result: Record<string, unknown>
}

export async function generateMCP(request: GenerateRequest): Promise<GenerateResponse> {
  const response = await fetch(`${API_BASE_URL}/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to generate MCP')
  }

  return response.json()
}

export async function testMCP(request: TestRequest): Promise<TestResponse> {
  const response = await fetch(`${API_BASE_URL}/test`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to test MCP')
  }

  return response.json()
}

export function downloadZip(zipData: string, filename: string = 'mcp_project.zip') {
  const bytes = new Uint8Array(zipData.length / 2)
  for (let i = 0; i < zipData.length; i += 2) {
    bytes[i / 2] = parseInt(zipData.substr(i, 2), 16)
  }
  
  const blob = new Blob([bytes], { type: 'application/zip' })
  const url = URL.createObjectURL(blob)
  
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}