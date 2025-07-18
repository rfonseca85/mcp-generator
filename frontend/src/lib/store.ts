import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { TestResponse } from './api'

export interface MCPConfig {
  openaiApiKey: string
  mcpName: string
  protocolTypes: ('stdio' | 'http' | 'sse')[]
  description: string
  version: string
  author: string
  baseUrl: string
}

const defaultConfig: MCPConfig = {
  openaiApiKey: '',
  mcpName: 'Generated MCP Server',
  protocolTypes: ['stdio'],
  description: 'MCP Server generated from API specification',
  version: '1.0.0',
  author: '',
  baseUrl: ''
}

interface AppState {
  isGenerating: boolean
  isTesting: boolean
  generationResult: string | null
  testResult: TestResponse | null
  config: MCPConfig
  setGenerating: (generating: boolean) => void
  setTesting: (testing: boolean) => void
  setGenerationResult: (result: string | null) => void
  setTestResult: (result: TestResponse | null) => void
  setConfig: (config: MCPConfig) => void
  updateConfig: (updates: Partial<MCPConfig>) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      isGenerating: false,
      isTesting: false,
      generationResult: null,
      testResult: null,
      config: defaultConfig,
      setGenerating: (generating) => set({ isGenerating: generating }),
      setTesting: (testing) => set({ isTesting: testing }),
      setGenerationResult: (result) => set({ generationResult: result }),
      setTestResult: (result) => set({ testResult: result }),
      setConfig: (config) => set({ config }),
      updateConfig: (updates) => set({ config: { ...get().config, ...updates } })
    }),
    {
      name: 'mcp-generator-storage',
      partialize: (state) => ({ config: state.config })
    }
  )
)