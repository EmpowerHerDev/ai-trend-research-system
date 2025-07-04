import asyncio
import os
from datetime import datetime
from typing import Dict, List, Any
from anthropic import Anthropic
from dotenv import load_dotenv

from keyword_manager import KeywordManager
from mcp_client_manager import MCPClientManager
from platform_handlers import PlatformHandlerFactory
from data_processor import KeywordExtractor, DataAnalyzer
from report_generator import ReportManager
from config_manager import ServerConfig, AppConfig, PlatformConfig

# Load environment variables
load_dotenv()


class AITrendResearcher:
    """Refactored AI Trend Researcher with modular architecture"""
    
    def __init__(self):
        # Initialize configuration
        AppConfig.print_config_status()
        
        # Initialize core components
        self.keyword_manager = KeywordManager()
        self.claude_client = Anthropic(api_key=AppConfig.get_anthropic_api_key())
        
        # Initialize server configurations
        server_configs = ServerConfig.get_server_configs()
        self.platforms = PlatformConfig.get_supported_platforms()
        
        # Initialize managers
        self.mcp_manager = MCPClientManager(server_configs)
        self.keyword_extractor = KeywordExtractor(self.claude_client)
        self.data_analyzer = DataAnalyzer()
        
        # Initialize report manager (will be set up after MCP connections)
        self.report_manager = None
    
    async def run_daily_research(self) -> str:
        """Run daily AI trend research with modular architecture"""
        print(f"Starting AI trend research - {datetime.now()}")
        
        try:
            # Connect to MCP servers
            await self.mcp_manager.connect_all_servers()
            
            # Set up report manager with Notion client if available
            notion_client = self.mcp_manager.get_client("notion")
            notion_parent_id = AppConfig.get_notion_parent_page_id()
            self.report_manager = ReportManager(
                reports_dir=AppConfig.get_reports_directory(),
                notion_client=notion_client,
                notion_parent_id=notion_parent_id
            )
            
            # Load and prepare keywords
            active_keywords = self._load_active_keywords()
            print(f"Researching {len(active_keywords)} keywords across {len(self.platforms)} platforms")
            
            # Conduct research
            research_data = await self._conduct_research(active_keywords)
            
            # Process research data
            new_keywords = await self.keyword_extractor.extract_keywords(research_data)
            keyword_scores = self.data_analyzer.score_keywords(new_keywords, research_data)
            summary = self.data_analyzer.calculate_summary_stats(research_data, new_keywords)
            recommendations = self.data_analyzer.generate_recommendations(research_data, new_keywords)
            
            # Update keyword manager
            self._update_keywords(new_keywords, keyword_scores, active_keywords)
            
            # Generate reports
            report_file = await self.report_manager.generate_all_reports(
                research_data, new_keywords, summary, recommendations
            )
            print(f"Report generated: {report_file}")
            
            # Record execution
            self.keyword_manager.record_execution(
                active_keywords, "completed", len(new_keywords)
            )
            
            print("Daily research completed successfully!")
            return report_file
            
        except Exception as e:
            print(f"Error in daily research: {e}")
            raise
        finally:
            await self.mcp_manager.close_all_clients()
    
    def _load_active_keywords(self) -> List[str]:
        """Load active keywords from keyword manager"""
        active_keywords = self.keyword_manager.load_active_keywords()
        if not active_keywords:
            print("No active keywords found. Refreshing from master list...")
            active_keywords = self.keyword_manager.refresh_active_keywords()
        return active_keywords
    
    async def _conduct_research(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Conduct research across all platforms and keywords"""
        all_research_data = []
        
        for keyword in keywords:
            for platform in self.platforms:
                try:
                    research_result = await self._research_platform_keyword(platform, keyword)
                    all_research_data.append(research_result)
                    print(f"✓ Completed research: {keyword} on {platform}")
                except Exception as e:
                    print(f"✗ Error researching {keyword} on {platform}: {e}")
                    # Add error result to maintain data consistency
                    error_result = {
                        "platform": platform,
                        "keyword": keyword,
                        "timestamp": datetime.now().isoformat(),
                        "results": [],
                        "new_keywords": [],
                        "sentiment_score": 0.0,
                        "engagement_metrics": {},
                        "error": str(e)
                    }
                    all_research_data.append(error_result)
        
        return all_research_data
    
    async def _research_platform_keyword(self, platform: str, keyword: str) -> Dict[str, Any]:
        """Research a specific platform for a keyword using appropriate handler"""
        # Check if platform is available via MCP
        if self.mcp_manager.is_platform_available(platform):
            try:
                handler = PlatformHandlerFactory.create_handler(platform, self.claude_client)
                client = self.mcp_manager.get_client(platform)
                config = ServerConfig.get_server_configs()[platform]
                
                return await handler.research_keyword(client, keyword, config)
                
            except Exception as e:
                print(f"Error with {platform} handler: {e}")
        
        # Return default empty result for unavailable platforms
        return {
            "platform": platform,
            "keyword": keyword,
            "timestamp": datetime.now().isoformat(),
            "results": [],
            "new_keywords": [],
            "sentiment_score": 0.0,
            "engagement_metrics": {},
            "error": f"Platform {platform} not available"
        }
    
    def _update_keywords(self, new_keywords: List[str], keyword_scores: Dict[str, int], 
                        active_keywords: List[str]):
        """Update keyword manager with new keywords and mark used ones"""
        # Add new keywords
        for keyword, score in keyword_scores.items():
            added = self.keyword_manager.add_new_keyword(
                keyword, score, "discovered", "daily_research"
            )
            if added:
                print(f"Added new keyword: {keyword} (score: {score})")
        
        # Mark keywords as used
        self.keyword_manager.mark_keywords_used(active_keywords)


async def main():
    """Main function with proper error handling and cleanup"""
    researcher = AITrendResearcher()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler():
        print("\n🛑 Received shutdown signal - forcing cleanup...")
        asyncio.create_task(force_cleanup_and_exit(researcher))
    
    if hasattr(asyncio, 'create_task'):
        import signal
        for sig in [signal.SIGTERM, signal.SIGINT]:
            try:
                asyncio.get_event_loop().add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass
    
    try:
        await researcher.run_daily_research()
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"Error in main execution: {e}")
        raise
    finally:
        # Cleanup is handled in run_daily_research()
        pass


async def force_cleanup_and_exit(researcher):
    """Force exit after timeout"""
    print("⚠ Force exiting...")
    try:
        await researcher.mcp_manager.close_all_clients()
    except Exception:
        pass
    import os
    os._exit(1)


if __name__ == "__main__":
    asyncio.run(main())