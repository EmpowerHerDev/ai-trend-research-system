import asyncio
import os
from typing import Dict, List, Any, Optional
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


class RemoteMCPClient:
    """MCP Client for connecting to local servers by name"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack: Optional[AsyncExitStack] = None
        self._connected = False
        self._cleanup_attempted = False
        self._available_tools: List[str] = []
        
    async def connect_to_server_by_name(self, server_name: str, args: List[str] = None, env: Dict[str, str] = None):
        """Connect to a local MCP server by name using stdio transport"""
        try:
            self.exit_stack = AsyncExitStack()
            
            server_params = StdioServerParameters(
                command=server_name,
                args=args or [],
                env=env
            )
            
            print(f"🔍 Connecting to {server_name} with args: {args}")
            if env:
                print(f"🔍 Environment variables: {list(env.keys())}")
            
            stdio_context = stdio_client(server_params)
            read_stream, write_stream = await self.exit_stack.enter_async_context(stdio_context)
            
            session_context = ClientSession(read_stream, write_stream)
            self.session = await self.exit_stack.enter_async_context(session_context)
            await self.session.initialize()
            
            response = await self.session.list_tools()
            tools = response.tools
            self._available_tools = [tool.name for tool in tools]
            print(f"✓ Connected to server '{server_name}' with tools: {self._available_tools}")
            
            # Print tool details for debugging
            for tool in tools:
                print(f"  - {tool.name}: {tool.description[:100]}...")
            
            self._connected = True
            return True
            
        except Exception as e:
            print(f"✗ Failed to connect to server '{server_name}': {e}")
            self._connected = False
            await self._cleanup()
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """Call a tool on the MCP server"""
        if not self.session or not self._connected:
            raise Exception("Not connected to any server")
        
        try:
            response = await self.session.call_tool(tool_name, arguments)
            if hasattr(response, 'content'):
                return response.content
            elif hasattr(response, 'result'):
                return response.result
            else:
                return response
        except Exception as e:
            print(f"✗ Error calling tool {tool_name}: {e}")
            return None
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return self._available_tools
    
    async def _cleanup(self):
        """Internal cleanup method with timeout"""
        if self._cleanup_attempted:
            return
        self._cleanup_attempted = True
        
        try:
            if self.exit_stack:
                # Add timeout to prevent hanging
                await asyncio.wait_for(self.exit_stack.aclose(), timeout=5.0)
        except asyncio.TimeoutError:
            print("Warning: Cleanup timeout, forcing close")
            # Force cleanup by setting to None
            self.exit_stack = None
        except asyncio.CancelledError:
            print("Warning: Cleanup was cancelled")
            # Handle cancellation gracefully
            self.exit_stack = None
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")
            self.exit_stack = None
    
    async def close(self):
        """Close the connection"""
        self._connected = False
        try:
            await asyncio.wait_for(self._cleanup(), timeout=10.0)
        except asyncio.TimeoutError:
            print("Warning: Close timeout, forcing cleanup")
        except asyncio.CancelledError:
            print("Warning: Close was cancelled")
        except Exception as e:
            print(f"Warning: Error during close: {e}")
        finally:
            self.session = None
            self.exit_stack = None


class MCPClientManager:
    """Manages multiple MCP client connections"""
    
    def __init__(self, server_configs: Dict[str, Dict]):
        self.server_configs = server_configs
        self.clients: Dict[str, RemoteMCPClient] = {}
    
    async def connect_all_servers(self):
        """Connect to all available MCP servers"""
        print("Connecting to MCP servers...")
        
        for platform, config in self.server_configs.items():
            if config.get("enabled", False):
                await self._connect_single_server(platform, config)
    
    async def _connect_single_server(self, platform: str, config: Dict):
        """Connect to a single MCP server"""
        try:
            mcp_client = RemoteMCPClient()
            
            args = config.get("args", [])
            env = config.get("env", {})
            success = await mcp_client.connect_to_server_by_name(
                config["server_name"], args, env
            )
            
            if success:
                self.clients[platform] = mcp_client
            else:
                self.clients[platform] = None
                
        except Exception as e:
            print(f"✗ Failed to connect to {platform} MCP server: {e}")
            self.clients[platform] = None
    
    def get_client(self, platform: str) -> Optional[RemoteMCPClient]:
        """Get MCP client for a specific platform"""
        return self.clients.get(platform)
    
    def is_platform_available(self, platform: str) -> bool:
        """Check if a platform's MCP client is available"""
        return platform in self.clients and self.clients[platform] is not None
    
    def get_available_tools(self, platform: str) -> List[str]:
        """Get available tools for a specific platform"""
        client = self.get_client(platform)
        if client:
            return client.get_available_tools()
        return []
    
    async def close_all_clients(self):
        """Close all MCP clients properly"""
        for platform, client in self.clients.items():
            if client:
                try:
                    await client.close()
                except Exception:
                    pass
        self.clients.clear()