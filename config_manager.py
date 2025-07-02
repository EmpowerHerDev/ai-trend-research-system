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
            "twitter": {
                "server_name": "twitter-mcp-server",
                "tools": ["search_tweets", "get_trending_topics"],
                "enabled": False
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
            "reddit": {
                "server_name": "reddit-mcp-server",
                "tools": ["search_posts", "get_subreddit_posts"],
                "enabled": False
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
                "server_name": "arxiv-mcp-server",
                "tools": ["search_papers", "get_recent_papers"],
                "enabled": False
            },
            "hackernews": {
                "server_name": "hackernews-mcp-server",
                "tools": ["search_posts", "get_top_stories"],
                "enabled": False
            },
            "producthunt": {
                "server_name": "producthunt-mcp-server",
                "tools": ["search_products", "get_trending_products"],
                "enabled": False
            },
            "linkedin": {
                "server_name": "linkedin-mcp-server",
                "tools": ["search_posts", "get_company_updates"],
                "enabled": False
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
            ("NOTION_PARENT_PAGE_ID", "Notion parent page ID")
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
        "github"
    ]
    
    @staticmethod
    def get_supported_platforms() -> List[str]:
        """Get list of supported platforms"""
        return PlatformConfig.SUPPORTED_PLATFORMS.copy()
    
    @staticmethod
    def is_platform_supported(platform: str) -> bool:
        """Check if platform is supported"""
        return platform in PlatformConfig.SUPPORTED_PLATFORMS