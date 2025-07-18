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
import { testMCP } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { TestTube, Loader2, CheckCircle, XCircle } from 'lucide-react';

export function MCPTester() {
  const [mcpConfig, setMcpConfig] = useState('');
  const [prompt, setPrompt] = useState('');
  const [mcpStatus, setMcpStatus] = useState<'unknown' | 'active' | 'inactive'>(
    'unknown'
  );
  const { isTesting, testResult, setTesting, setTestResult } = useAppStore();

  const checkMcpStatus = async (configText: string) => {
    if (!configText.trim()) {
      setMcpStatus('unknown');
      return;
    }

    try {
      const config = JSON.parse(configText);
      const servers = config.mcpServers || {};
      const serverEntries = Object.entries(servers);

      if (serverEntries.length === 0) {
        setMcpStatus('inactive');
        return;
      }

      // Check the first server
      const [, serverConfig] = serverEntries[0] as [string, { url?: string }];
      const url = serverConfig.url;

      if (!url) {
        setMcpStatus('inactive');
        return;
      }

      // Try to ping the MCP server
      try {
        const response = await fetch(url, {
          method: 'GET',
          signal: AbortSignal.timeout(5000) // 5 second timeout
        });

        if (response.ok) {
          setMcpStatus('active');
        } else {
          setMcpStatus('inactive');
        }
      } catch {
        setMcpStatus('inactive');
      }
    } catch {
      setMcpStatus('unknown');
    }
  };

  const handleConfigChange = (value: string) => {
    setMcpConfig(value);
    checkMcpStatus(value);
  };

  const handleTest = async () => {
    if (!mcpConfig.trim() || !prompt.trim()) {
      alert('Please fill in both MCP configuration and prompt');
      return;
    }

    setTesting(true);
    try {
      const config = JSON.parse(mcpConfig);
      const result = await testMCP({
        mcp_config: config,
        prompt: prompt
      });

      setTestResult(result);
    } catch (error) {
      console.error('Testing failed:', error);
      alert('Failed to test MCP: ' + (error as Error).message);
    } finally {
      setTesting(false);
    }
  };

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TestTube className="w-5 h-5" />
          MCP Tester
        </CardTitle>
        <CardDescription>
          Test your MCP server by sending prompts and viewing responses
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <label htmlFor="mcp-config" className="text-sm font-medium">
              MCP Configuration (JSON)
            </label>
            {mcpStatus === 'active' && (
              <div
                className="w-2 h-2 bg-green-500 rounded-full"
                title="MCP Server Active"
              ></div>
            )}
            {mcpStatus === 'inactive' && (
              <div
                className="w-2 h-2 bg-red-500 rounded-full"
                title="MCP Server Inactive"
              ></div>
            )}
          </div>
          <Textarea
            id="mcp-config"
            placeholder="Enter your MCP server configuration..."
            value={mcpConfig}
            onChange={(e) => handleConfigChange(e.target.value)}
            className="min-h-[120px] font-mono text-sm"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="prompt" className="text-sm font-medium">
            Test Prompt
          </label>
          <Textarea
            id="prompt"
            placeholder="Enter a prompt to test the MCP server..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="min-h-[100px]"
          />
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleTest}
          disabled={isTesting || !mcpConfig.trim() || !prompt.trim()}
          className="w-full"
        >
          {isTesting ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Testing MCP Server...
            </>
          ) : (
            <>
              <TestTube className="w-4 h-4 mr-2" />
              Test MCP Server
            </>
          )}
        </Button>

        {testResult && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Test Results</h3>
            <div className="space-y-2">
              {Object.entries(testResult.result as Record<string, any>).map(
                ([serverName, result]: [string, any]) => (
                  <Card
                    key={serverName}
                    className="border-l-4 border-l-blue-500"
                  >
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base flex items-center gap-2">
                        {result.error ? (
                          <XCircle className="w-4 h-4 text-red-500" />
                        ) : (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        )}
                        {serverName}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {result.error ? (
                        <div className="text-red-600 text-sm">
                          <strong>Error:</strong> {result.error}
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <div className="text-sm">
                            <strong>Status:</strong> {result.status}
                          </div>
                          <div className="text-sm">
                            <strong>Available Tools:</strong>{' '}
                            {result.available_tools?.length || 0}
                          </div>
                          {result.available_tools &&
                            result.available_tools.length > 0 && (
                              <div className="text-sm">
                                <strong>Available Tools:</strong>
                                <ul className="list-disc list-inside mt-1 space-y-1">
                                  {result.available_tools.map(
                                    (
                                      tool: Record<string, unknown>,
                                      index: number
                                    ) => (
                                      <li key={index}>
                                        {String(tool.name)} -{' '}
                                        {String(tool.description)}
                                      </li>
                                    )
                                  )}
                                </ul>
                              </div>
                            )}
                          {result.tool_calls &&
                            result.tool_calls.length > 0 && (
                              <div className="text-sm">
                                <strong>Tool Executions:</strong>
                                <div className="mt-1 space-y-2">
                                  {result.tool_calls.map(
                                    (toolCall: any, index: number) => (
                                      <div
                                        key={index}
                                        className="p-2 bg-gray-50 rounded border-l-4 border-l-blue-400"
                                      >
                                        <div className="flex items-center gap-2">
                                          {toolCall.success ? (
                                            <CheckCircle className="w-3 h-3 text-green-500" />
                                          ) : (
                                            <XCircle className="w-3 h-3 text-red-500" />
                                          )}
                                          <strong>{toolCall.tool}</strong>
                                        </div>
                                        {toolCall.arguments &&
                                          Object.keys(toolCall.arguments)
                                            .length > 0 && (
                                            <div className="text-xs text-gray-600 mt-1">
                                              <strong>Arguments:</strong>{' '}
                                              {JSON.stringify(
                                                toolCall.arguments
                                              )}
                                            </div>
                                          )}
                                        {toolCall.success ? (
                                          <div className="text-xs text-gray-700 mt-1">
                                            <strong>Result:</strong>
                                            <pre className="mt-1 p-1 bg-white rounded text-xs overflow-x-auto">
                                              {JSON.stringify(
                                                toolCall.result,
                                                null,
                                                2
                                              )}
                                            </pre>
                                          </div>
                                        ) : (
                                          <div className="text-xs text-red-600 mt-1">
                                            <strong>Error:</strong>{' '}
                                            {toolCall.error}
                                          </div>
                                        )}
                                      </div>
                                    )
                                  )}
                                </div>
                              </div>
                            )}
                          <div className="text-sm">
                            <strong>Response:</strong>
                            <pre className="mt-1 p-2 bg-gray-100 rounded text-xs overflow-x-auto">
                              {result.response}
                            </pre>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )
              )}
            </div>
          </div>
        )}

        <div className="text-sm text-muted-foreground">
          <p>
            <strong>How to use:</strong> Make sure your MCP server is running,
            then test it with different prompts.
          </p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>The configuration should point to your running MCP server</li>
            <li>
              The prompt will be used to test the server&apos;s capabilities
            </li>
            <li>Results will show available tools and server responses</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
