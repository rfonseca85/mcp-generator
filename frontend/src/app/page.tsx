'use client';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MCPGenerator } from '@/components/mcp-generator';
import { MCPTester } from '@/components/mcp-tester';
import { MCPConfig } from '@/components/mcp-config';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            MCP Generator & Tester
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Transform API specifications into fully functional MCP servers and
            test them with ease
          </p>
        </div>

        <Tabs defaultValue="generator" className="w-full">
          <TabsList className="grid w-full grid-cols-3 max-w-lg mx-auto mb-8">
            <TabsTrigger value="generator">Generator</TabsTrigger>
            <TabsTrigger value="tester">Tester</TabsTrigger>
            <TabsTrigger value="config">Config</TabsTrigger>
          </TabsList>

          <TabsContent value="generator" className="space-y-6">
            <MCPGenerator />
          </TabsContent>

          <TabsContent value="tester" className="space-y-6">
            <MCPTester />
          </TabsContent>

          <TabsContent value="config" className="space-y-6">
            <MCPConfig />
          </TabsContent>
        </Tabs>

        <footer className="mt-16 text-center text-sm text-gray-500">
          <p>
            Built with Next.js, FastAPI, and OpenAI •
            <a href="https://github.com" className="ml-1 hover:underline">
              View on GitHub
            </a>
          </p>
        </footer>
      </div>
    </div>
  );
}
