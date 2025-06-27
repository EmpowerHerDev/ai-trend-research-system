import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from anthropic import Anthropic
from keyword_manager import KeywordManager
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.stdio import StdioServerParameters
from contextlib import AsyncExitStack
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class RemoteMCPClient:
    """MCP Client for connecting to local servers by name"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.transport = None
        
    async def connect_to_server_by_name(self, server_name: str):
        """Connect to a local MCP server by name using stdio transport"""
        try:
            # Create stdio server parameters for the named server
            server_params = StdioServerParameters(
                command=server_name,
                args=[],
                env=None
            )
            
            # Connect using stdio transport
            self.transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.session = await self.exit_stack.enter_async_context(ClientSession(*self.transport))
            await self.session.initialize()
            
            # List available tools
            response = await self.session.list_tools()
            tools = response.tools
            print(f"✓ Connected to server '{server_name}' with tools: {[tool.name for tool in tools]}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to connect to server '{server_name}': {e}")
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """Call a tool on the MCP server"""
        if not self.session:
            raise Exception("Not connected to any server")
        
        try:
            response = await self.session.call_tool(tool_name, arguments)
            # Handle different response formats
            if hasattr(response, 'content'):
                return response.content
            elif hasattr(response, 'result'):
                return response.result
            else:
                return response
        except Exception as e:
            print(f"✗ Error calling tool {tool_name}: {e}")
            return None
    
    async def close(self):
        """Close the connection"""
        try:
            if self.exit_stack:
                await self.exit_stack.aclose()
        except Exception as e:
            print(f"Warning: Error closing MCP client: {e}")

class AITrendResearcher:
    def __init__(self):
        self.keyword_manager = KeywordManager()
        self.reports_dir = "reports"
        self.claude_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        print(os.getenv("ANTHROPIC_API_KEY"))
        self.mcp_clients = {}  # Dictionary to store multiple MCP clients
        # self.platforms = [
        #     "twitter", "youtube", "web", "github", "reddit", 
        #     "linkedin", "arxiv", "hackernews", "producthunt"
        # ]
        self.platforms = [
            "web",
        ]

        # MCP server configurations using server names
        self.mcp_servers = {
            "youtube": {
                "server_name": "youtube-mcp-server",
                "tools": ["search_videos", "get_video_details"],
                "enabled": False
            },
            "twitter": {
                "server_name": "twitter-mcp-server",
                "tools": ["search_tweets", "get_trending_topics"],
                "enabled": False
            },
            "github": {
                "server_name": "github-mcp-server",
                "tools": ["search_repositories", "get_trending_repos"],
                "enabled": False
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
    
    async def connect_mcp_servers(self):
        """Connect to all available MCP servers by name"""
        print("Connecting to MCP servers...")
        
        for platform, config in self.mcp_servers.items():
            if config["enabled"]:
                try:
                    mcp_client = RemoteMCPClient()
                    
                    # Connect to server by name
                    success = await mcp_client.connect_to_server_by_name(config["server_name"])
                    
                    if success:
                        self.mcp_clients[platform] = mcp_client
                    else:
                        self.mcp_clients[platform] = None
                        
                except Exception as e:
                    print(f"✗ Failed to connect to {platform} MCP server: {e}")
                    self.mcp_clients[platform] = None
    
    async def _research_via_mcp(self, platform: str, keyword: str) -> Optional[Dict[str, Any]]:
        """Research via remote MCP server for a specific platform"""
        if platform not in self.mcp_clients or not self.mcp_clients[platform]:
            return None
        
        try:
            client = self.mcp_clients[platform]
            config = self.mcp_servers[platform]
            
            # Use the first available tool for the platform
            tool_name = config["tools"][0]
            
            # Platform-specific parameters
            params = {"query": keyword, "max_results": 10}
            
            if platform == "youtube":
                params["order"] = "relevance"
            elif platform == "github":
                params["sort"] = "stars"
            elif platform == "reddit":
                params["subreddit"] = "MachineLearning"
            elif platform == "arxiv":
                params["max_results"] = 5
            elif platform == "hackernews":
                params["time_range"] = "week"
            
            response = await client.call_tool(tool_name, params)
            print(f"MCP response: {response}")
            return self._process_mcp_response(platform, response, keyword)
            
        except Exception as e:
            print(f"{platform.capitalize()} MCP error: {e}")
            return {
                "platform": platform,
                "keyword": keyword,
                "timestamp": datetime.now().isoformat(),
                "results": [],
                "new_keywords": [],
                "sentiment_score": 0.0,
                "engagement_metrics": {},
                "error": str(e)
            }
    
    def _process_mcp_response(self, platform: str, response: Any, keyword: str) -> Dict[str, Any]:
        """Process MCP response for any platform"""
        results = []
        
        # Process MCP response format
        if hasattr(response, 'content') and response.content:
            data = response.content
        elif isinstance(response, dict):
            data = response
        elif isinstance(response, list) and len(response) > 0:
            # Handle list of TextContent objects (like from one-search-mcp)
            first_item = response[0]
            if hasattr(first_item, 'text'):
                data = first_item.text
            else:
                data = response
        else:
            data = {}
        
        # Platform-specific processing
        if platform == "youtube":
            videos = data.get('videos', data.get('items', []))
            for video in videos:
                results.append({
                    'title': video.get('title', ''),
                    'description': video.get('description', ''),
                    'published_at': video.get('published_at', video.get('publishedAt', '')),
                    'channel': video.get('channel_title', video.get('channelTitle', '')),
                    'video_id': video.get('video_id', video.get('videoId', '')),
                    'view_count': video.get('view_count', 0),
                    'duration': video.get('duration', '')
                })
        
        elif platform == "twitter":
            tweets = data.get('tweets', data.get('data', []))
            for tweet in tweets:
                results.append({
                    'text': tweet.get('text', ''),
                    'author': tweet.get('author', tweet.get('username', '')),
                    'created_at': tweet.get('created_at', ''),
                    'retweet_count': tweet.get('retweet_count', 0),
                    'like_count': tweet.get('like_count', 0),
                    'tweet_id': tweet.get('id', '')
                })
        
        elif platform == "github":
            repos = data.get('repositories', data.get('items', []))
            for repo in repos:
                results.append({
                    'name': repo.get('name', ''),
                    'description': repo.get('description', ''),
                    'owner': repo.get('owner', {}).get('login', ''),
                    'stars': repo.get('stargazers_count', 0),
                    'language': repo.get('language', ''),
                    'url': repo.get('html_url', ''),
                    'created_at': repo.get('created_at', '')
                })
        
        elif platform == "reddit":
            posts = data.get('posts', data.get('data', {}).get('children', []))
            for post in posts:
                post_data = post.get('data', post)
                results.append({
                    'title': post_data.get('title', ''),
                    'text': post_data.get('selftext', ''),
                    'author': post_data.get('author', ''),
                    'score': post_data.get('score', 0),
                    'subreddit': post_data.get('subreddit', ''),
                    'url': post_data.get('url', ''),
                    'created_utc': post_data.get('created_utc', '')
                })
        
        elif platform == "web":
            print(f"Web MCP response type: {type(data)}")
            
            # Handle text-based response from one-search-mcp
            if isinstance(data, str):
                results = self._parse_web_search_text(data)
            else:
                # Handle structured data
                web_results = data.get('results', data.get('items', []))
                for result in web_results:
                    results.append({
                        'title': result.get('title', ''),
                        'snippet': result.get('snippet', result.get('description', '')),
                        'url': result.get('url', result.get('link', '')),
                        'source': result.get('source', '')
                    })
        
        elif platform == "arxiv":
            papers = data.get('papers', data.get('entries', []))
            for paper in papers:
                results.append({
                    'title': paper.get('title', ''),
                    'abstract': paper.get('summary', paper.get('abstract', '')),
                    'authors': paper.get('authors', []),
                    'published_date': paper.get('published', ''),
                    'arxiv_id': paper.get('id', ''),
                    'categories': paper.get('categories', [])
                })
        
        elif platform == "hackernews":
            stories = data.get('stories', data.get('hits', []))
            for story in stories:
                results.append({
                    'title': story.get('title', ''),
                    'url': story.get('url', ''),
                    'author': story.get('author', ''),
                    'points': story.get('points', story.get('score', 0)),
                    'comments_count': story.get('comments_count', 0),
                    'created_at': story.get('created_at', '')
                })
        
        elif platform == "producthunt":
            products = data.get('products', data.get('posts', []))
            for product in products:
                results.append({
                    'name': product.get('name', ''),
                    'tagline': product.get('tagline', ''),
                    'description': product.get('description', ''),
                    'votes': product.get('votes_count', 0),
                    'category': product.get('category', {}).get('name', ''),
                    'url': product.get('url', '')
                })
        
        elif platform == "linkedin":
            posts = data.get('posts', data.get('elements', []))
            for post in posts:
                results.append({
                    'text': post.get('text', ''),
                    'author': post.get('author', ''),
                    'likes': post.get('likes_count', 0),
                    'comments': post.get('comments_count', 0),
                    'created_at': post.get('created_at', '')
                })
        
        return {
            "platform": platform,
            "keyword": keyword,
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "new_keywords": [],
            "sentiment_score": 0.0,
            "engagement_metrics": {
                f"total_{platform}_items": len(results)
            }
        }
    
    def _parse_web_search_text(self, text: str) -> List[Dict[str, str]]:
        """Parse web search results from text format"""
        results = []
        
        # Split by double newlines to separate results
        sections = text.split('\n\n\n')
        
        for section in sections:
            if not section.strip():
                continue
                
            lines = section.strip().split('\n')
            if len(lines) < 2:
                continue
            
            # Parse title and URL from first line
            title_line = lines[0]
            if title_line.startswith('Title: '):
                title = title_line[7:]  # Remove "Title: " prefix
            else:
                title = title_line
            
            # Parse URL from second line
            url = ""
            if len(lines) > 1 and lines[1].startswith('URL: '):
                url = lines[1][5:]  # Remove "URL: " prefix
            
            # Parse description from remaining lines
            description = ""
            if len(lines) > 2 and lines[2].startswith('Description: '):
                description = lines[2][13:]  # Remove "Description: " prefix
                # Add any additional description lines
                for line in lines[3:]:
                    if line.strip() and not line.startswith('URL: '):
                        description += " " + line.strip()
            
            if title and url:  # Only add if we have at least title and URL
                results.append({
                    'title': title,
                    'snippet': description,
                    'url': url,
                    'source': self._extract_domain_from_url(url)
                })
        
        print(f"Parsed {len(results)} web search results from text")
        return results
    
    def _extract_domain_from_url(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return ""
    
    async def extract_new_keywords(self, research_data: List[Dict]) -> List[str]:
        """Extract new keywords using Claude AI"""
        if not research_data or not self.claude_client:
            print("No research data or Claude client available for keyword extraction")
            return []
        
        # Prepare content for Claude analysis
        content_summary = []
        for data in research_data:
            if data.get('results'):
                for result in data['results'][:3]:  # Limit to first 3 results per platform
                    content_summary.append({
                        'platform': data['platform'],
                        'keyword': data['keyword'],
                        'title': result.get('title', ''),
                        'description': result.get('description', result.get('snippet', ''))[:200]  # Limit description length
                    })
        
        if not content_summary:
            print("No content found in research data for keyword extraction")
            return []
        
        try:
            prompt = f"""Analyze this AI trend research data and extract 5-10 new trending keywords related to AI, machine learning, or technology.
            
Data: {json.dumps(content_summary, indent=2, ensure_ascii=False)}
            
Instructions:
1. Focus on AI tools, frameworks, companies, techniques, or emerging technologies
2. Return only a JSON array of keywords, like: ["keyword1", "keyword2", "keyword3"]
3. Prioritize keywords that appear frequently or have high engagement
4. Include both English and Japanese keywords if relevant
5. If no relevant keywords are found, return an empty array: []
"""
            
            response = await self._call_claude(prompt)
            keywords = self._parse_keywords_from_response(response)
            print(f"Claude extracted {len(keywords)} keywords: {keywords}")
            return keywords
            
        except Exception as e:
            print(f"Claude keyword extraction error: {e}")
            return []
    
    async def _call_claude(self, prompt: str) -> str:
        """Call Claude API asynchronously"""
        message = self.claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    
    def _parse_keywords_from_response(self, response: str) -> List[str]:
        """Parse keywords from Claude response"""
        try:
            # Try to extract JSON array from response
            import re
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                keywords = json.loads(json_match.group())
                return [k.strip() for k in keywords if isinstance(k, str) and k.strip()]
        except Exception as e:
            print(f"Error parsing keywords: {e}")
        
        # Fallback: extract words that look like keywords
        words = response.replace('"', '').replace('[', '').replace(']', '').split(',')
        return [w.strip() for w in words if w.strip() and len(w.strip()) > 2][:10]
    
    async def score_keywords(self, keywords: List[str], research_data: List[Dict]) -> Dict[str, int]:
        """Score new keywords based on research data"""
        # Mock scoring based on mentions and engagement
        scores = {}
        for keyword in keywords:
            # Simple scoring algorithm
            base_score = 50
            mention_count = sum(1 for data in research_data if keyword.lower() in str(data).lower())
            scores[keyword] = min(100, base_score + mention_count * 5)
        
        return scores
    
    async def generate_report(self, research_data: List[Dict], new_keywords: List[str]) -> str:
        """Generate research report"""
        today = datetime.now().strftime("%Y-%m-%d")
        report = {
            "date": today,
            "summary": {
                "platforms_searched": len(set(d["platform"] for d in research_data)),
                "keywords_used": list(set(d["keyword"] for d in research_data)),
                "new_keywords_found": len(new_keywords),
                "total_results": sum(len(d["results"]) for d in research_data)
            },
            "detailed_results": research_data,
            "new_keywords": new_keywords,
            "recommendations": self._generate_recommendations(research_data, new_keywords)
        }
        
        report_file = os.path.join(self.reports_dir, f"ai_trends_{today}.json")
        os.makedirs(self.reports_dir, exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report_file
    
    def _generate_recommendations(self, research_data: List[Dict], new_keywords: List[str]) -> List[str]:
        """Generate recommendations based on research"""
        recommendations = []
        
        if new_keywords:
            recommendations.append(f"Consider adding {len(new_keywords)} new keywords to monitoring")
        
        high_engagement_platforms = [d["platform"] for d in research_data if d.get("sentiment_score", 0) > 0.7]
        if high_engagement_platforms:
            recommendations.append(f"High engagement detected on: {', '.join(set(high_engagement_platforms))}")
        
        return recommendations
    
    async def run_daily_research(self):
        """Run daily AI trend research"""
        print(f"Starting AI trend research - {datetime.now()}")
        
        try:
            # Initialize MCP connections
            await self.connect_mcp_servers()
            
            # Load active keywords
            active_keywords = self.keyword_manager.load_active_keywords()
            if not active_keywords:
                print("No active keywords found. Refreshing from master list...")
                active_keywords = self.keyword_manager.refresh_active_keywords()
            
            print(f"Researching {len(active_keywords)} keywords across {len(self.platforms)} platforms")
            
            # Research each keyword on each platform
            all_research_data = []
            for keyword in active_keywords:
                for platform in self.platforms:
                    try:
                        research_result = await self.research_platform(platform, keyword)
                        all_research_data.append(research_result)
                        print(f"✓ Completed research: {keyword} on {platform}")
                    except Exception as e:
                        print(f"✗ Error researching {keyword} on {platform}: {e}")
            
            print(all_research_data)
            # Extract new keywords
            new_keywords = await self.extract_new_keywords(all_research_data)
            print(f"Found {len(new_keywords)} new keywords: {new_keywords}")
            
            # Score and add new keywords to master list
            if new_keywords:
                keyword_scores = await self.score_keywords(new_keywords, all_research_data)
                for keyword, score in keyword_scores.items():
                    added = self.keyword_manager.add_new_keyword(
                        keyword, score, "discovered", "daily_research"
                    )
                    if added:
                        print(f"Added new keyword: {keyword} (score: {score})")
            
            # Mark keywords as used
            self.keyword_manager.mark_keywords_used(active_keywords)
            
            # Generate report
            report_file = await self.generate_report(all_research_data, new_keywords)
            print(f"Report generated: {report_file}")
            
            # Record execution
            self.keyword_manager.record_execution(
                active_keywords, "completed", len(new_keywords)
            )
            
            print("Daily research completed successfully!")
            return report_file
            
        finally:
            # Clean up MCP connections
            print("Cleaning up MCP connections...")
            for client in self.mcp_clients.values():
                if client:
                    try:
                        await client.close()
                    except Exception as e:
                        print(f"Warning: Error closing MCP client: {e}")

    async def research_platform(self, platform: str, keyword: str) -> Dict[str, Any]:
        """Research a specific platform for a keyword"""
        print(f"Researching {platform} for {keyword}")
        # Try MCP server first
        if platform in self.mcp_servers and self.mcp_servers[platform]["enabled"]:
            mcp_result = await self._research_via_mcp(platform, keyword)
            if mcp_result and not mcp_result.get("error"):
                return mcp_result
        
        # Default mock data for unsupported platforms
        return {
            "platform": platform,
            "keyword": keyword,
            "timestamp": datetime.now().isoformat(),
            "results": [],
            "new_keywords": [],
            "sentiment_score": 0.0,
            "engagement_metrics": {}
        }

async def main():
    researcher = AITrendResearcher()
    try:
        await researcher.run_daily_research()
    except Exception as e:
        print(f"Error in main execution: {e}")
        raise
    finally:
        # Ensure all MCP clients are properly closed
        for client in researcher.mcp_clients.values():
            if client:
                try:
                    await client.close()
                except Exception as e:
                    print(f"Warning: Error closing MCP client: {e}")

if __name__ == "__main__":
    asyncio.run(main())