'use client';

import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { generateMCP, downloadZip } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { Download, FileCode, Loader2 } from 'lucide-react';

interface ParsedTool {
  id: string;
  name: string;
  description: string;
  method: string;
  path: string;
  selected: boolean;
}

export function MCPGenerator() {
  const [apiSpec, setApiSpec] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [parsedTools, setParsedTools] = useState<ParsedTool[]>([]);
  const [showToolSelection, setShowToolSelection] = useState(false);
  const { isGenerating, setGenerating, setGenerationResult, config } =
    useAppStore();

  const parseApiSpec = () => {
    if (!apiSpec.trim()) {
      alert('Please provide an API specification first');
      return;
    }

    try {
      const spec = JSON.parse(apiSpec);
      const tools: ParsedTool[] = [];

      if (spec.paths) {
        Object.entries(spec.paths).forEach(([path, methods]) => {
          Object.entries(methods as Record<string, unknown>).forEach(
            ([method, operation]) => {
              const op = operation as Record<string, unknown>;
              const operationId =
                (op.operationId as string) ||
                `${method}_${path.replace(/[^a-zA-Z0-9]/g, '_')}`;
              const description =
                (op.description as string) ||
                (op.summary as string) ||
                `${method.toUpperCase()} ${path}`;

              tools.push({
                id: `${method}_${path}`,
                name: operationId,
                description,
                method: method.toUpperCase(),
                path,
                selected: true // Default to selected
              });
            }
          );
        });
      }

      setParsedTools(tools);
      setShowToolSelection(true);
    } catch {
      alert(
        'Invalid JSON in API specification. Please check your JSON syntax.'
      );
    }
  };

  const toggleToolSelection = (toolId: string) => {
    setParsedTools((tools) =>
      tools.map((tool) =>
        tool.id === toolId ? { ...tool, selected: !tool.selected } : tool
      )
    );
  };

  const selectAllTools = () => {
    setParsedTools((tools) =>
      tools.map((tool) => ({ ...tool, selected: true }))
    );
  };

  const deselectAllTools = () => {
    setParsedTools((tools) =>
      tools.map((tool) => ({ ...tool, selected: false }))
    );
  };

  const handleGenerate = async () => {
    if (!apiSpec.trim() || !systemPrompt.trim()) {
      alert('Please fill in both API specification and system prompt');
      return;
    }

    // Check if tools are selected when tool selection is shown
    if (showToolSelection) {
      const selectedTools = parsedTools.filter((tool) => tool.selected);
      if (selectedTools.length === 0) {
        alert('Please select at least one tool to generate');
        return;
      }
    }

    setGenerating(true);
    try {
      const selectedToolIds = showToolSelection
        ? parsedTools.filter((tool) => tool.selected).map((tool) => tool.id)
        : undefined;

      const result = await generateMCP({
        api_spec: apiSpec,
        system_prompt: systemPrompt,
        base_url: baseUrl.trim() || config.baseUrl || undefined,
        selected_tools: selectedToolIds,
        config: {
          openai_api_key: config.openaiApiKey,
          mcp_name: config.mcpName,
          protocol_types: config.protocolTypes,
          description: config.description,
          version: config.version,
          author: config.author
        }
      });

      setGenerationResult(result.zip_data);
      downloadZip(result.zip_data);
    } catch (error) {
      console.error('Generation failed:', error);
      alert('Failed to generate MCP: ' + (error as Error).message);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileCode className="w-5 h-5" />
          MCP Generator
        </CardTitle>
        <CardDescription>
          Generate a Model Context Protocol (MCP) server from an API
          specification and system prompt
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Configuration Summary */}
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
          <div className="text-sm text-blue-800">
            <strong>Current Configuration:</strong> {config.mcpName} •{' '}
            {config.protocolTypes.map((p) => p.toUpperCase()).join(' + ')}{' '}
            protocols
            {config.openaiApiKey ? ' • OpenAI configured' : ' • No OpenAI key'}
          </div>
        </div>
        <div className="space-y-2">
          <label htmlFor="api-spec" className="text-sm font-medium">
            API Specification (OpenAPI/Swagger JSON)
          </label>
          <Textarea
            id="api-spec"
            placeholder="Paste your OpenAPI/Swagger JSON specification here..."
            value={apiSpec}
            onChange={(e) => setApiSpec(e.target.value)}
            className="min-h-[200px] font-mono text-sm"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={parseApiSpec}
            disabled={!apiSpec.trim()}
            className="mt-2"
          >
            Load APIs that will become tools
          </Button>
        </div>

        {showToolSelection && (
          <div className="space-y-4">
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-medium">
                  Select Tools to Generate
                </h3>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={selectAllTools}>
                    Select All
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={deselectAllTools}
                  >
                    Deselect All
                  </Button>
                </div>
              </div>
              <div className="text-sm text-muted-foreground mb-3">
                Found {parsedTools.length} API endpoints. Select which ones you
                want as MCP tools:
              </div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {parsedTools.map((tool) => (
                  <div
                    key={tool.id}
                    className="flex items-start space-x-3 p-2 border rounded hover:bg-gray-50"
                  >
                    <input
                      type="checkbox"
                      id={tool.id}
                      checked={tool.selected}
                      onChange={() => toggleToolSelection(tool.id)}
                      className="mt-1"
                    />
                    <div className="flex-1 min-w-0">
                      <label
                        htmlFor={tool.id}
                        className="text-sm font-medium cursor-pointer"
                      >
                        {tool.name}
                      </label>
                      <div className="text-xs text-muted-foreground">
                        {tool.method} {tool.path}
                      </div>
                      <div className="text-xs text-gray-600 mt-1">
                        {tool.description}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="space-y-2">
          <label htmlFor="base-url" className="text-sm font-medium">
            Base URL (Optional)
          </label>
          <Textarea
            id="base-url"
            placeholder={`Enter the base URL for API calls (e.g., https://api.example.com). ${
              config.baseUrl
                ? `Default: ${config.baseUrl}`
                : 'Leave empty to use the servers section from your API spec.'
            }`}
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            className="min-h-[60px]"
          />
          <div className="text-xs text-muted-foreground">
            This URL will be used as the base for all API calls made by the
            generated MCP tools. If not specified, the generator will use the
            {config.baseUrl ? ' configured default base URL or the' : ''} first
            server URL from your OpenAPI specification.
          </div>
        </div>

        <div className="space-y-2">
          <label htmlFor="system-prompt" className="text-sm font-medium">
            System Prompt
          </label>
          <Textarea
            id="system-prompt"
            placeholder="Enter the system prompt that describes how the AI should behave..."
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            className="min-h-[100px]"
          />
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleGenerate}
          disabled={isGenerating || !apiSpec.trim() || !systemPrompt.trim()}
          className="w-full"
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Generating MCP Project...
            </>
          ) : (
            <>
              <Download className="w-4 h-4 mr-2" />
              Generate & Download MCP Project
            </>
          )}
        </Button>

        {!config.openaiApiKey && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
            <div className="text-sm text-yellow-800">
              <strong>Note:</strong> OpenAI API key is required for AI-enhanced
              tool descriptions. Go to the <strong>Config</strong> tab to set up
              your API key and other preferences.
            </div>
          </div>
        )}

        <div className="text-sm text-muted-foreground">
          <p>
            <strong>What you&apos;ll get:</strong> A ZIP file containing a
            complete MCP server project with:
          </p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>Python MCP server implementation</li>
            <li>API tools mapped to MCP tools</li>
            <li>Dockerfile for containerization</li>
            <li>README with setup instructions</li>
            <li>Configuration examples for Cursor and Claude Desktop</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
