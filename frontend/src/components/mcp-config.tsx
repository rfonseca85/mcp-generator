'use client';

import React from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useAppStore } from '@/lib/store';
import { Settings, Save, Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';

export function MCPConfig() {
  const { config, updateConfig } = useAppStore();
  const [showApiKey, setShowApiKey] = useState(false);
  const [tempConfig, setTempConfig] = useState(config);

  // Sync tempConfig when config changes (e.g., on page load)
  React.useEffect(() => {
    setTempConfig(config);
  }, [config]);

  const handleSave = () => {
    updateConfig(tempConfig);
    alert('Configuration saved successfully!');
  };

  const handleReset = () => {
    setTempConfig(config);
  };

  const hasChanges = JSON.stringify(tempConfig) !== JSON.stringify(config);

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="w-5 h-5" />
          MCP Configuration
        </CardTitle>
        <CardDescription>
          Configure your MCP generation settings. These settings are saved
          locally in your browser.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label htmlFor="openai-key" className="text-sm font-medium">
              OpenAI API Key *
            </label>
            <div className="relative">
              <input
                id="openai-key"
                type={showApiKey ? 'text' : 'password'}
                placeholder="sk-..."
                value={tempConfig.openaiApiKey}
                onChange={(e) =>
                  setTempConfig((prev) => ({
                    ...prev,
                    openaiApiKey: e.target.value
                  }))
                }
                className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm pr-10"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-2 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
                onClick={() => setShowApiKey(!showApiKey)}
              >
                {showApiKey ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>
            </div>
            <div className="text-xs text-muted-foreground">
              Required for AI-enhanced tool descriptions. This replaces the
              environment variable.
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="mcp-name" className="text-sm font-medium">
              MCP Server Name
            </label>
            <Textarea
              id="mcp-name"
              placeholder="My Custom MCP Server"
              value={tempConfig.mcpName}
              onChange={(e) =>
                setTempConfig((prev) => ({
                  ...prev,
                  mcpName: e.target.value
                }))
              }
              className="min-h-[40px]"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">
              Protocol Types (Select multiple)
            </label>
            <div className="space-y-3 p-3 border border-input rounded-md">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="protocol-stdio"
                  checked={tempConfig.protocolTypes.includes('stdio')}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setTempConfig((prev) => ({
                      ...prev,
                      protocolTypes: checked
                        ? [...prev.protocolTypes, 'stdio']
                        : prev.protocolTypes.filter((p) => p !== 'stdio')
                    }));
                  }}
                  className="rounded"
                />
                <label htmlFor="protocol-stdio" className="text-sm">
                  <strong>STDIO</strong> - Recommended for Cursor/Claude Desktop
                </label>
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="protocol-http"
                  checked={tempConfig.protocolTypes.includes('http')}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setTempConfig((prev) => ({
                      ...prev,
                      protocolTypes: checked
                        ? [...prev.protocolTypes, 'http']
                        : prev.protocolTypes.filter((p) => p !== 'http')
                    }));
                  }}
                  className="rounded"
                />
                <label htmlFor="protocol-http" className="text-sm">
                  <strong>HTTP</strong> - For testing and web integration
                </label>
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="protocol-sse"
                  checked={tempConfig.protocolTypes.includes('sse')}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setTempConfig((prev) => ({
                      ...prev,
                      protocolTypes: checked
                        ? [...prev.protocolTypes, 'sse']
                        : prev.protocolTypes.filter((p) => p !== 'sse')
                    }));
                  }}
                  className="rounded"
                />
                <label htmlFor="protocol-sse" className="text-sm">
                  <strong>SSE</strong> - Server-Sent Events for real-time
                  communication
                </label>
              </div>
            </div>
            <div className="text-xs text-muted-foreground">
              Select one or more communication protocols for your MCP server.
              Multiple protocols will be supported in the same project.
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="version" className="text-sm font-medium">
              Version
            </label>
            <Textarea
              id="version"
              placeholder="1.0.0"
              value={tempConfig.version}
              onChange={(e) =>
                setTempConfig((prev) => ({
                  ...prev,
                  version: e.target.value
                }))
              }
              className="min-h-[40px]"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="author" className="text-sm font-medium">
              Author
            </label>
            <Textarea
              id="author"
              placeholder="Your Name or Organization"
              value={tempConfig.author}
              onChange={(e) =>
                setTempConfig((prev) => ({
                  ...prev,
                  author: e.target.value
                }))
              }
              className="min-h-[40px]"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="base-url" className="text-sm font-medium">
              Default Base URL
            </label>
            <Textarea
              id="base-url"
              placeholder="https://api.example.com"
              value={tempConfig.baseUrl}
              onChange={(e) =>
                setTempConfig((prev) => ({
                  ...prev,
                  baseUrl: e.target.value
                }))
              }
              className="min-h-[40px]"
            />
            <div className="text-xs text-muted-foreground">
              Default base URL for API calls (can be overridden per generation)
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <label htmlFor="description" className="text-sm font-medium">
            Default Description
          </label>
          <Textarea
            id="description"
            placeholder="Description for your MCP server"
            value={tempConfig.description}
            onChange={(e) =>
              setTempConfig((prev) => ({
                ...prev,
                description: e.target.value
              }))
            }
            className="min-h-[80px]"
          />
        </div>

        <div className="flex gap-4 pt-4">
          <Button
            onClick={handleSave}
            disabled={!hasChanges || tempConfig.protocolTypes.length === 0}
            className="flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            Save Configuration
          </Button>

          <Button
            variant="outline"
            onClick={handleReset}
            disabled={!hasChanges}
          >
            Reset Changes
          </Button>
        </div>

        {!tempConfig.openaiApiKey && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
            <div className="text-sm text-yellow-800">
              <strong>Note:</strong> OpenAI API key is required for AI-enhanced
              tool descriptions. Without it, basic tool descriptions will be
              generated.
            </div>
          </div>
        )}

        {tempConfig.protocolTypes.length === 0 && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="text-sm text-red-800">
              <strong>Error:</strong> At least one protocol must be selected.
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
