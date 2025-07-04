import os
from typing import Dict, List, Any


class ServerConfig:
    """Configuration for MCP servers"""
    
    @staticmethod
    def get_server_configs() -> Dict[str, Dict[str, Any]]:
        """Get MCP server configurations"""
        return {
            "youtube": {
                "server_name": "npx",
                "args": ["-y", "youtube-data-mcp-server"],
                "env": {
                    "YOUTUBE_API_KEY": os.getenv("YOUTUBE_API_KEY"),
                    "YOUTUBE_TRANSCRIPT_LANG": "ja"
                },
                "tools": ["searchVideos", "getVideoDetails", "getTranscripts"],
                "enabled": True
            },
            "github": {
                "server_name": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-github"
                ],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
                },
                "tools": ["search_code", "search_repositories", "get_repository"],
                "enabled": True
            },
            "web": {
                "server_name": "one-search-mcp",
                "tools": ["one_search", "one_extract", "one_scrape"],
                "enabled": True
            },
            "notion": {
                "server_name": "npx",
                "args": ["@ramidecodes/mcp-server-notion@latest", "-y", f"--api-key={os.getenv('NOTION_API_KEY')}"],
                "tools": ["create-page", "get-page", "update-page", "query-database", "search"],
                "enabled": True
            },
            "arxiv": {
                "server_name": "npx",
                "args": ["-y", "@langgpt/arxiv-mcp-server@latest"],
                "env": {
                    "SILICONFLOW_API_KEY": os.getenv("SILICONFLOW_API_KEY"),
                    "WORK_DIR": "./reports"
                },
                "tools":  ['search_arxiv', 'download_arxiv_pdf', 'parse_pdf_to_text', 'convert_to_wechat_article', 'parse_pdf_to_markdown', 'process_arxiv_paper', 'clear_workdir'],
                "enabled": True
            },
            "hackernews": {
                "server_name": "npx",
                "args": ["-y", "@microagents/server-hackernews"],
                "tools": ["getStories", "getStory", "getStoryWithComments"],
                "enabled": True
            }
        }
    
    @staticmethod
    def get_enabled_platforms() -> List[str]:
        """Get list of enabled platforms"""
        configs = ServerConfig.get_server_configs()
        return [platform for platform, config in configs.items() if config.get("enabled", False)]


class AppConfig:
    """Application configuration"""
    
    @staticmethod
    def get_anthropic_api_key() -> str:
        """Get Anthropic API key"""
        return os.getenv("ANTHROPIC_API_KEY", "")
    
    @staticmethod
    def get_notion_parent_page_id() -> str:
        """Get Notion parent page ID"""
        return os.getenv("NOTION_PARENT_PAGE_ID", "")
    
    @staticmethod
    def get_reports_directory() -> str:
        """Get reports directory path"""
        return "reports"
    
    @staticmethod
    def validate_required_env_vars() -> List[str]:
        """Validate required environment variables and return missing ones"""
        required_vars = {
            "ANTHROPIC_API_KEY": "Anthropic API key for Claude",
            "YOUTUBE_API_KEY": "YouTube API key", 
            "GITHUB_PERSONAL_ACCESS_TOKEN": "GitHub access token",
            "NOTION_API_KEY": "Notion API key",
            "NOTION_PARENT_PAGE_ID": "Notion parent page ID"
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"{var} ({description})")
        
        return missing_vars
    
    @staticmethod
    def print_config_status():
        """Print configuration status"""
        print("=== Configuration Status ===")
        
        # Check Anthropic API key
        if os.getenv("ANTHROPIC_API_KEY"):
            print("✓ Anthropic API key loaded")
        else:
            print("✗ Anthropic API key not found")
        
        # Check other important keys
        env_vars = [
            ("YOUTUBE_API_KEY", "YouTube API key"),
            ("GITHUB_PERSONAL_ACCESS_TOKEN", "GitHub access token"),
            ("NOTION_API_KEY", "Notion API key"),
            ("NOTION_PARENT_PAGE_ID", "Notion parent page ID"),
            ("SILICONFLOW_API_KEY", "Siliconflow API key")
        ]
        
        for var, description in env_vars:
            if os.getenv(var):
                print(f"✓ {description} loaded")
            else:
                print(f"✗ {description} not found")
        
        print("============================")


class PlatformConfig:
    """Platform-specific configurations"""
    
    SUPPORTED_PLATFORMS = [
        "web", 
        "youtube", 
        "github",
        "arxiv",
        "hackernews",
    ]
    
    @staticmethod
    def get_supported_platforms() -> List[str]:
        """Get list of supported platforms"""
        return PlatformConfig.SUPPORTED_PLATFORMS.copy()
    
    @staticmethod
    def is_platform_supported(platform: str) -> bool:
        """Check if platform is supported"""
        return platform in PlatformConfig.SUPPORTED_PLATFORMS