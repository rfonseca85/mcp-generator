# MCP Generator & Tester

A powerful full-stack application that transforms OpenAPI/Swagger specifications into fully functional Model Context Protocol (MCP) servers with intelligent AI-enhanced tool generation and comprehensive testing capabilities.

## 🎯 What is This Project?

The MCP Generator & Tester is a comprehensive solution that bridges the gap between traditional APIs and the emerging Model Context Protocol (MCP) ecosystem. It automatically converts your existing API specifications into MCP-compliant servers that can be seamlessly integrated with AI assistants like Claude Desktop and Cursor.

### Key Benefits

- **Rapid MCP Adoption**: Convert existing APIs to MCP in minutes, not hours
- **AI-Enhanced Generation**: Uses OpenAI GPT to create intelligent tool descriptions and parameter validation
- **Multiple Protocol Support**: Generate servers supporting STDIO, HTTP, and SSE protocols
- **Production Ready**: Generated servers include Docker support, error handling, and comprehensive documentation
- **Testing Suite**: Built-in testing tools to validate MCP server functionality

## 🏗️ How It Works

### Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │  Generated MCP  │
│   (Next.js)     │    │   (FastAPI)     │    │     Server      │
│                 │    │                 │    │                 │
│ • Generator UI  │◄──►│ • OpenAPI       │───►│ • Tool Handlers │
│ • Tester UI     │    │   Parser        │    │ • JSON-RPC      │
│ • Config UI     │    │ • AI Enhancement│    │ • Multi-Protocol│
│                 │    │ • Code Gen      │    │ • Docker Ready  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Generation Workflow

1. **API Specification Input**: Users provide OpenAPI/Swagger JSON specification
2. **Intelligent Parsing**: Backend parses the API spec and extracts endpoints, parameters, and schemas
3. **AI Enhancement**: OpenAI GPT analyzes each endpoint and generates:
   - Clear, contextual tool descriptions
   - Enhanced parameter documentation
   - Intelligent naming conventions
4. **Code Generation**: Creates a complete MCP server project with:
   - Tool handlers that make HTTP calls to the original API
   - Multiple protocol support (STDIO/HTTP/SSE)
   - Docker configuration
   - Comprehensive documentation
5. **Package & Download**: Generates a ZIP file with the complete project

### Testing Workflow

1. **Server Detection**: Automatically detects if MCP servers are running
2. **Tool Discovery**: Queries the server for available tools via JSON-RPC
3. **AI-Powered Execution**: Uses OpenAI to determine which tools to call based on user prompts
4. **Result Analysis**: Executes tools and provides detailed feedback on success/failure

## 🚀 Features

### MCP Generator
- **Smart OpenAPI Parsing**: Handles complex schemas with `$ref` resolution and `allOf`/`oneOf` support
- **AI-Enhanced Descriptions**: Uses GPT-3.5 to create meaningful tool descriptions and parameter docs
- **Multi-Protocol Support**: Generates servers supporting:
  - **STDIO**: Direct communication for Cursor/Claude Desktop integration
  - **HTTP**: RESTful API for web integration and testing
  - **SSE**: Server-Sent Events for real-time bidirectional communication
- **Complete Project Generation**: Creates production-ready servers with:
  - Async/await Python handlers
  - Docker containerization
  - Shell scripts for easy deployment
  - Comprehensive README documentation
  - Configuration files for popular MCP clients

### MCP Tester
- **Intelligent Testing**: Uses AI to determine appropriate tool calls based on natural language prompts
- **Real-time Validation**: Tests server connectivity and tool availability
- **Multiple Server Support**: Can test multiple MCP servers simultaneously
- **Detailed Reporting**: Provides comprehensive feedback on tool execution results

### Configuration Management
- **Persistent Settings**: Browser-based local storage for user preferences
- **OpenAI Integration**: Configurable API key for AI enhancements
- **Protocol Selection**: Choose which transport protocols to support
- **Custom Naming**: Set custom server names and descriptions

## 🛠️ Tech Stack

### Frontend
- **Next.js 15**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **shadcn/ui**: Modern component library
- **Zustand**: Lightweight state management

### Backend
- **FastAPI**: High-performance async Python framework
- **OpenAI GPT-3.5**: AI-powered code enhancement
- **Pydantic**: Data validation and serialization
- **HTTPX**: Async HTTP client for testing

### Generated Servers
- **FastAPI**: High-performance server framework
- **JSON-RPC 2.0**: MCP protocol implementation
- **Async/Await**: Non-blocking I/O operations
- **Docker**: Containerization support

## 📦 Installation & Setup

### Prerequisites
- **Node.js 18+**: For frontend development
- **Python 3.11+**: For backend services
- **Docker**: (Optional) For containerized deployment
- **OpenAI API Key**: For AI-enhanced generation

### Quick Start with Docker
```bash
# Clone the repository
git clone <repository-url>
cd mcp-generator

# Create environment file
cp .env.example .env
# Edit .env and add your OpenAI API key

# Start with Docker Compose
docker-compose up
```

### Manual Development Setup

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
export OPENAI_API_KEY=your_api_key_here
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

The application will be available at `http://localhost:3000`

## 📖 Usage Guide

### Generating MCP Servers

1. **Access the Generator**
   - Open `http://localhost:3000`
   - Navigate to the "Generator" tab

2. **Configure Settings** (Optional)
   - Go to "Config" tab
   - Set OpenAI API key for enhanced descriptions
   - Configure server name and protocol preferences

3. **Provide API Specification**
   - Paste your OpenAPI/Swagger JSON in the text area
   - Click "Load APIs that will become tools" to preview available endpoints

4. **Select Tools** (Optional)
   - Review the parsed endpoints
   - Select/deselect specific tools to include
   - Each endpoint becomes an MCP tool

5. **Add System Prompt**
   - Provide a system prompt describing the AI behavior
   - This guides how the MCP server should behave when integrated with AI assistants

6. **Set Base URL** (Optional)
   - Specify the base URL for API calls
   - If omitted, uses the server URL from your OpenAPI spec

7. **Generate & Download**
   - Click "Generate & Download MCP Project"
   - A ZIP file will download containing your complete MCP server

### Generated Project Structure

```
mcp_project/
├── main.py              # Entry point with protocol selection
├── mcp_server.py        # Core MCP server (STDIO/HTTP)
├── sse_server.py        # SSE server (if selected)
├── handlers.py          # Generated tool handlers
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container configuration
├── run.sh              # Deployment script
├── prompt.txt          # System prompt
├── metadata.json       # Generation metadata
└── README.md           # Usage instructions
```

### Using Generated Servers

#### For Cursor Integration
Add to `.cursor/config.json`:
```json
{
  "mcpServers": {
    "your-api": {
      "command": "python",
      "args": ["main.py"],
      "cwd": "/path/to/your/mcp_project"
    }
  }
}
```

#### For Claude Desktop Integration
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "your-api": {
      "command": "python",
      "args": ["main.py"],
      "cwd": "/path/to/your/mcp_project"
    }
  }
}
```

#### For HTTP/SSE Integration
```json
{
  "mcpServers": {
    "your-api": {
      "url": "http://localhost:8080",
      "transport": "http"
    }
  }
}
```

### Testing MCP Servers

1. **Start Your MCP Server**
   ```bash
   cd mcp_project
   chmod +x run.sh
   ./run.sh http  # For HTTP testing
   ```

2. **Access the Tester**
   - Go to the "Tester" tab in the web interface
   - Enter your MCP server configuration:
   ```json
   {
     "mcpServers": {
       "test-server": {
         "url": "http://localhost:8080"
       }
     }
   }
   ```

3. **Test with Prompts**
   - Enter natural language prompts like:
     - "List all available tools"
     - "Create a new user with name John"
     - "Get user information for ID 123"
   - The tester uses AI to determine appropriate tool calls

4. **Review Results**
   - See which tools were called
   - View execution results and any errors
   - Validate server functionality

## 🔧 Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key          # Required for AI enhancement
NEXT_PUBLIC_API_URL=http://localhost:8000   # Backend API URL
```

### MCP Configuration Options
- **MCP Server Name**: Custom name for generated server
- **Protocol Types**: Select STDIO, HTTP, and/or SSE support
- **Description**: Custom description for the server
- **Version**: Semantic version for the generated server
- **Author**: Author information
- **Base URL**: Default base URL for API calls

## 🎛️ Advanced Features

### AI Enhancement
The generator uses OpenAI GPT-3.5 to enhance tool definitions:
- **Smart Descriptions**: Converts technical API descriptions into user-friendly explanations
- **Parameter Documentation**: Adds helpful parameter descriptions and usage notes
- **Tool Naming**: Generates clean, consistent tool names from API operations

### Multi-Protocol Support
Generated servers can support multiple transport protocols simultaneously:
- **STDIO**: For direct integration with AI assistants
- **HTTP**: For web applications and testing
- **SSE**: For real-time applications requiring bidirectional communication

### Error Handling
Generated servers include comprehensive error handling:
- **Parameter Validation**: Validates required parameters before API calls
- **HTTP Error Mapping**: Maps HTTP errors to MCP error responses
- **Graceful Degradation**: Continues operation even when individual tools fail

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test thoroughly
4. Commit your changes: `git commit -m 'Add amazing feature'`
5. Push to the branch: `git push origin feature/amazing-feature`
6. Submit a pull request

### Development Guidelines
- Follow TypeScript/Python best practices
- Add tests for new functionality
- Update documentation for any API changes
- Ensure all existing tests pass

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

MIT License allows you to:
- ✅ Use the software for any purpose
- ✅ Modify and distribute the software
- ✅ Include in commercial projects
- ✅ Patent use (as long as you include the license)

The only requirement is to include the original license and copyright notice in any substantial portions of the software.

## 🔗 Links & Resources

- [Model Context Protocol Documentation](https://docs.modelcontextprotocol.org/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Claude Desktop Configuration](https://docs.anthropic.com/claude/docs/desktop-configuration)
- [Cursor MCP Integration](https://docs.cursor.so/mcp)

## 🐛 Troubleshooting

### Common Issues

**Generation fails with "Invalid JSON"**
- Ensure your OpenAPI specification is valid JSON
- Use tools like [JSON Validator](https://jsonlint.com/) to check syntax

**Generated server won't start**
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify the base URL is accessible from your server
- Check the logs for specific error messages

**MCP client can't connect**
- Ensure the server is running and accessible
- Verify the configuration file syntax
- Check that the specified port is not in use

**Tools return errors**
- Verify the base URL is correct and accessible
- Check that required parameters are provided
- Ensure the original API is available and responding

## 🙏 Acknowledgments

- Built with the Model Context Protocol specification
- Uses OpenAI's GPT models for intelligent code generation
- Inspired by the need for better API-to-MCP conversion tools
- Thanks to the FastAPI and Next.js communities for excellent frameworks