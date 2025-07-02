import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from anthropic import Anthropic
from keyword_manager import KeywordManager
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.stdio import StdioServerParameters
from contextlib import AsyncExitStack
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

class RemoteMCPClient:
    """MCP Client for connecting to local servers by name"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack: Optional[AsyncExitStack] = None
        self._connected = False
        self._cleanup_attempted = False
        
    async def connect_to_server_by_name(self, server_name: str, args: List[str] = None, env: Dict[str, str] = None):
        """Connect to a local MCP server by name using stdio transport"""
        try:
            # Create exit stack to manage contexts properly
            self.exit_stack = AsyncExitStack()
            
            # Create stdio server parameters for the named server
            server_params = StdioServerParameters(
                command=server_name,
                args=args or [],
                env=env
            )
            
            # Connect using stdio transport with proper context management
            stdio_context = stdio_client(server_params)
            read_stream, write_stream = await self.exit_stack.enter_async_context(stdio_context)
            
            # Create session with proper context management
            session_context = ClientSession(read_stream, write_stream)
            self.session = await self.exit_stack.enter_async_context(session_context)
            await self.session.initialize()
            
            # List available tools
            response = await self.session.list_tools()
            tools = response.tools
            print(f"✓ Connected to server '{server_name}' with tools: {[tool.name for tool in tools]}")
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
    
    async def _cleanup(self):
        """Internal cleanup method with timeout"""
        if self._cleanup_attempted:
            return
        self._cleanup_attempted = True
        
        try:
            if self.exit_stack:
                # Close gracefully without timeout to avoid task context issues
                await self.exit_stack.aclose()
        except Exception as e:
            # Suppress all exceptions during cleanup to prevent shutdown errors
            pass
    
    async def close(self):
        """Close the connection"""
        self._connected = False
        await self._cleanup()
        self.session = None
        self.exit_stack = None

class AITrendResearcher:
    def __init__(self):
        self.keyword_manager = KeywordManager()
        self.reports_dir = "reports"
        self.claude_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        # Verify API key is loaded (don't print the actual key)
        if os.getenv("ANTHROPIC_API_KEY"):
            print("✓ Anthropic API key loaded")
        else:
            print("✗ Anthropic API key not found")
        self.mcp_clients = {}  # Dictionary to store multiple MCP clients
        self.platforms = [
            "web",
            "youtube",
            "github",
        ]

        # MCP server configurations using server names
        self.mcp_servers = {
            "youtube": {
                "server_name": "npx",
                "args": ["-y", "youtube-data-mcp-server"],
                "env": {
                    "YOUTUBE_API_KEY": os.getenv("YOUTUBE_API_KEY"),
                    "YOUTUBE_TRANSCRIPT_LANG": "ja"  # Changed to Japanese for your use case
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
    
    async def connect_mcp_servers(self):
        """Connect to all available MCP servers by name"""
        print("Connecting to MCP servers...")
        
        for platform, config in self.mcp_servers.items():
            if config["enabled"]:
                try:
                    mcp_client = RemoteMCPClient()
                    
                    # Connect to server by name
                    args = config.get("args", [])
                    env = config.get("env", {})
                    success = await mcp_client.connect_to_server_by_name(config["server_name"], args, env)
                    
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
                params["type"] = "video"  # Only search for videos
                params["max_results"] = 15  # Get more results for better analysis
                # Use just the keyword without additional restrictions for better results
                params["query"] = keyword
            elif platform == "github":     
                # GitHub-specific search parameters
                params = {
                    "query": f"{keyword} followers:>1000 stars:>50",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 10
                }
                tool_name = "search_repositories"
            elif platform == "reddit":
                params["subreddit"] = "MachineLearning"
            elif platform == "arxiv":
                params["max_results"] = 5
            elif platform == "hackernews":
                params["time_range"] = "week"
            elif platform == "web":
                # Add Japanese language preference for web search
                params["query"] = f"{keyword} 日本語"
                params["language"] = "ja"
                params["region"] = "jp"
            
            print(f"Searching {platform} for keyword: {keyword}")
            response = await client.call_tool(tool_name, params)
            print(f"{platform.capitalize()} MCP response type: {type(response)}")
            print(f"{platform.capitalize()} MCP response: {response}")
            
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
        data = {}  # Initialize data variable
        
        # Process MCP response format
        if isinstance(response, list) and len(response) > 0:
            # Handle list of TextContent objects (like from youtube-data-mcp-server or one-search-mcp)
            first_item = response[0]
            if hasattr(first_item, 'text'):
                # For web platform, parse the text directly as search results
                if platform == "web":
                    results = self._parse_web_search_text(first_item.text)
                else:
                    # For other platforms, try to parse as JSON
                    try:
                        import json
                        data = json.loads(first_item.text)
                    except (json.JSONDecodeError, AttributeError):
                        data = {}
            else:
                data = response
        elif hasattr(response, 'content') and response.content:
            data = response.content
        elif isinstance(response, dict):
            # Handle structured data - check if it contains TextContent objects
            if 'results' in response or 'items' in response:
                # Standard structured format
                web_results = response.get('results', response.get('items', []))
                for result in web_results:
                    results.append({
                        'title': result.get('title', ''),
                        'snippet': result.get('snippet', result.get('description', '')),
                        'url': result.get('url', result.get('link', '')),
                        'source': result.get('source', '')
                    })
            else:
                # Dictionary with TextContent objects (one-search-mcp format)
                # Look for any list in the dictionary
                for key, value in response.items():
                    if isinstance(value, list) and len(value) > 0:
                        first_item = value[0]
                        if hasattr(first_item, 'text'):
                            if platform == "web":
                                results = self._parse_web_search_text(first_item.text)
                            break
        else:
            data = {}
        
        # Platform-specific processing
        if platform == "youtube":
            # Handle different YouTube response formats
            if isinstance(data, list):
                # Direct list of video items (YouTube API format)
                videos = data
            else:
                # Dictionary format with 'videos' or 'items' keys
                videos = data.get('videos', data.get('items', []))
            
            for video in videos:
                # Extract data from YouTube API response structure
                snippet = video.get('snippet', {})
                video_id = video.get('id', {}).get('videoId', '')
                
                # Classify content type based on title and description
                content_type = self._classify_youtube_content(
                    snippet.get('title', ''),
                    snippet.get('description', '')
                )
                
                results.append({
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', ''),
                    'published_at': snippet.get('publishedAt', ''),
                    'channel': snippet.get('channelTitle', ''),
                    'video_id': video_id,
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'content_type': content_type,
                    'language': self._detect_language(snippet.get('title', '') + ' ' + snippet.get('description', ''))
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
            # Handle GitHub repository search results
            repos = []
            
            # Extract repositories from different response formats
            if isinstance(data, list):
                repos = data
            elif isinstance(data, dict):
                repos = data.get('repositories', data.get('items', data.get('data', [])))
            
            # Handle TextContent objects for GitHub responses
            if not repos and isinstance(response, list) and len(response) > 0:
                first_item = response[0]
                if hasattr(first_item, 'text'):
                    try:
                        import json
                        parsed_data = json.loads(first_item.text)
                        if isinstance(parsed_data, list):
                            repos = parsed_data
                        elif isinstance(parsed_data, dict):
                            repos = parsed_data.get('repositories', parsed_data.get('items', parsed_data.get('data', [])))
                    except (json.JSONDecodeError, AttributeError):
                        repos = self._parse_github_text_response(first_item.text)
            
            # Process repositories
            for repo in repos:
                if isinstance(repo, dict):
                    # Extract owner information
                    owner_data = repo.get('owner', {})
                    owner = owner_data.get('login', '') if isinstance(owner_data, dict) else str(owner_data)
                    
                    # Extract basic repository data
                    stars = repo.get('stargazers_count', repo.get('stars', 0))
                    created_at = repo.get('created_at', '')
                    updated_at = repo.get('updated_at', '')
                    
                    # Calculate trend metrics
                    star_rate, days_old, is_trending, is_accelerating = self._calculate_github_trend_metrics(
                        stars, created_at
                    )
                    
                    results.append({
                        'name': repo.get('name', ''),
                        'description': repo.get('description', ''),
                        'owner': owner,
                        'stars': stars,
                        'language': repo.get('language', ''),
                        'url': repo.get('html_url', repo.get('url', '')),
                        'created_at': created_at,
                        'forks': repo.get('forks_count', repo.get('forks', 0)),
                        'topics': repo.get('topics', []),
                        'license': repo.get('license', {}).get('name', '') if repo.get('license') else '',
                        'updated_at': updated_at,
                        'size': repo.get('size', 0),
                        'open_issues': repo.get('open_issues_count', 0),
                        # Trend analysis
                        'star_rate': round(star_rate, 2),
                        'days_old': days_old,
                        'is_trending': is_trending,
                        'is_accelerating': is_accelerating,
                        'trend_score': self._calculate_trend_score(stars, days_old, star_rate)
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
            print(f"Web MCP response type: {type(response)}")
            print(f"Web MCP response data: {response}")
            
            # If results are already populated from TextContent parsing above, use them
            if not results:
                # Handle text-based response from one-search-mcp
                if isinstance(data, str):
                    results = self._parse_web_search_text(data)
                elif isinstance(data, dict):
                    # Handle structured data - check if it contains TextContent objects
                    if 'results' in data or 'items' in data:
                        # Standard structured format
                        web_results = data.get('results', data.get('items', []))
                        for result in web_results:
                            results.append({
                                'title': result.get('title', ''),
                                'snippet': result.get('snippet', result.get('description', '')),
                                'url': result.get('url', result.get('link', '')),
                                'source': result.get('source', '')
                            })
                    else:
                        # Dictionary with TextContent objects (one-search-mcp format)
                        # Look for any list in the dictionary
                        for key, value in data.items():
                            if isinstance(value, list) and len(value) > 0:
                                first_item = value[0]
                                if hasattr(first_item, 'text'):
                                    results = self._parse_web_search_text(first_item.text)
                                    break
                else:
                    # Handle list of TextContent objects
                    if isinstance(data, list) and len(data) > 0:
                        first_item = data[0]
                        if hasattr(first_item, 'text'):
                            results = self._parse_web_search_text(first_item.text)
            
            print(f"Parsed {len(results)} web results")
        
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
            "engagement_metrics": self._calculate_engagement_metrics(platform, results)
        }
    
    def _parse_web_search_text(self, text: str) -> List[Dict[str, str]]:
        """Parse web search results from text format"""
        results = []
        
        # Split by double newlines to separate results (one-search-mcp format)
        sections = text.split('\n\n')
        
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
    
    def _parse_github_text_response(self, text: str) -> List[Dict[str, Any]]:
        """Parse GitHub repository results from text format"""
        results = []
        
        # Split by double newlines to separate repository entries
        sections = text.split('\n\n')
        
        for section in sections:
            if not section.strip():
                continue
                
            lines = section.strip().split('\n')
            if len(lines) < 2:
                continue
            
            repo_info = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('Name: '):
                    repo_info['name'] = line[6:]
                elif line.startswith('Owner: '):
                    repo_info['owner'] = line[7:]
                elif line.startswith('Description: '):
                    repo_info['description'] = line[13:]
                elif line.startswith('URL: '):
                    repo_info['url'] = line[5:]
                elif line.startswith('Stars: '):
                    try:
                        repo_info['stars'] = int(line[7:])
                    except ValueError:
                        repo_info['stars'] = 0
                elif line.startswith('Language: '):
                    repo_info['language'] = line[10:]
                elif line.startswith('Created: '):
                    repo_info['created_at'] = line[9:]
                elif line.startswith('Forks: '):
                    try:
                        repo_info['forks'] = int(line[7:])
                    except ValueError:
                        repo_info['forks'] = 0
                elif line.startswith('Topics: '):
                    topics_str = line[8:]
                    repo_info['topics'] = [t.strip() for t in topics_str.split(',') if t.strip()]
            
            # Only add if we have at least name and owner
            if repo_info.get('name') and repo_info.get('owner'):
                results.append({
                    'name': repo_info.get('name', ''),
                    'description': repo_info.get('description', ''),
                    'owner': repo_info.get('owner', ''),
                    'stars': repo_info.get('stars', 0),
                    'language': repo_info.get('language', ''),
                    'url': repo_info.get('url', ''),
                    'created_at': repo_info.get('created_at', ''),
                    'forks': repo_info.get('forks', 0),
                    'topics': repo_info.get('topics', []),
                    'license': '',
                    'updated_at': '',
                    'size': 0,
                    'open_issues': 0
                })
        
        print(f"Parsed {len(results)} GitHub repositories from text")
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
        
        # Also create Notion report
        await self.create_notion_report(report)
        
        return report_file
    
    async def create_notion_report(self, report: Dict):
        """Create organized report in Notion using MCP server"""
        if not self.mcp_clients.get("notion"):
            print("Notion MCP server not available, skipping Notion report")
            return
        
        try:
            today = report["date"]
            page_title = f"AI Trend Research Report - {today}"
            
            # Prepare page content
            content = self._format_notion_content(report)
            
            # Create page using MCP server
            parent_id = os.getenv("NOTION_PARENT_PAGE_ID", "")
            if not parent_id:
                print("NOTION_PARENT_PAGE_ID not set, skipping Notion report")
                return
                
            response = await self.mcp_clients["notion"].call_tool(
                "create-page",
                {
                    "parent_type": "page_id",
                    "parent_id": parent_id,
                    "properties": json.dumps({
                        "title": {
                            "title": [{"text": {"content": page_title}}]
                        }
                    }),
                    "children": json.dumps(self._create_notion_blocks(report))
                }
            )
            
            print(f"✓ Notion report created: {page_title}")
            return response
            
        except Exception as e:
            print(f"✗ Error creating Notion report: {e}")

    def _format_notion_content(self, report: Dict) -> str:
        """Format report data for Notion"""
        today = report["date"]
        summary = report["summary"]
        new_keywords = report["new_keywords"]
        recommendations = report["recommendations"]
        
        content = f"""# AI Trend Research Report - {today}

## 📊 Summary
- **Platforms Searched**: {summary['platforms_searched']}
- **Keywords Used**: {', '.join(summary['keywords_used'])}
- **New Keywords Found**: {summary['new_keywords_found']}
- **Total Results**: {summary['total_results']}

## 🔍 New Keywords Discovered
"""
        
        if new_keywords:
            for keyword in new_keywords:
                content += f"- {keyword}\n"
        else:
            content += "- No new keywords found\n"
        
        content += "\n## 📋 Recommendations\n"
        for rec in recommendations:
            content += f"- {rec}\n"
        
        content += "\n## 🔬 Detailed Research Results\n"
        
        # Group results by platform
        platform_results = {}
        for data in report["detailed_results"]:
            platform = data["platform"]
            if platform not in platform_results:
                platform_results[platform] = []
            platform_results[platform].extend(data["results"])
        
        for platform, results in platform_results.items():
            content += f"\n### {platform.upper()}\n"
            if results:
                for i, result in enumerate(results[:5], 1):  # Limit to top 5 results
                    title = result.get('title', result.get('name', 'No title'))
                    url = result.get('url', result.get('link', ''))
                    snippet = result.get('snippet', result.get('description', ''))[:200]
                    
                    content += f"\n#### {i}. {title}\n"
                    if url:
                        content += f"🔗 {url}\n"
                    if snippet:
                        content += f"📝 {snippet}...\n"
            else:
                content += "- No results found\n"
        
        return content
    
    def _create_notion_blocks(self, report: Dict) -> List[Dict]:
        """Create Notion blocks from report data"""
        blocks = []
        
        # Add summary section
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📊 Summary"}}]
            }
        })
        
        summary = report["summary"]
        summary_text = f"• Platforms Searched: {summary['platforms_searched']}\n"
        summary_text += f"• Keywords Used: {', '.join(summary['keywords_used'])}\n"
        summary_text += f"• New Keywords Found: {summary['new_keywords_found']}\n"
        summary_text += f"• Total Results: {summary['total_results']}"
        
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": summary_text}}]
            }
        })
        
        # Add new keywords section
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🔍 New Keywords Discovered"}}]
            }
        })
        
        if report["new_keywords"]:
            for keyword in report["new_keywords"]:
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": keyword}}]
                    }
                })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": "No new keywords found"}}]
                }
            })
        
        return blocks
    
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
            # Properly close MCP connections
            await self._close_all_mcp_clients()


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
    
    async def _close_all_mcp_clients(self):
        """Close all MCP clients properly"""
        for platform, client in self.mcp_clients.items():
            if client:
                try:
                    await client.close()
                except Exception:
                    # Suppress all exceptions during shutdown
                    pass
        self.mcp_clients.clear()

    def _classify_youtube_content(self, title: str, description: str) -> str:
        """Classify YouTube content type based on title and description"""
        text = (title + ' ' + description).lower()
        
        # Japanese keywords for content classification
        if any(keyword in text for keyword in ['解説', '説明', '入門', '基礎', '学習', 'チュートリアル']):
            return "解説動画"  # Explanatory video
        elif any(keyword in text for keyword in ['デモ', 'デモンストレーション', '実演', '動作確認', 'サンプル']):
            return "デモ"  # Demo
        elif any(keyword in text for keyword in ['カンファレンス', 'セミナー', '講演', '発表', 'conference', 'talk']):
            return "カンファレンス"  # Conference
        elif any(keyword in text for keyword in ['ニュース', '最新', 'アップデート', 'リリース']):
            return "ニュース"  # News
        elif any(keyword in text for keyword in ['レビュー', '比較', '検証', '評価']):
            return "レビュー"  # Review
        else:
            return "その他"  # Other

    def _detect_language(self, text: str) -> str:
        """Detect language of the text"""
        # Simple Japanese character detection
        japanese_chars = set('あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン')
        
        # Check if text contains Japanese characters
        if any(char in japanese_chars for char in text):
            return "ja"  # Japanese
        elif any(char.isascii() for char in text):
            return "en"  # English
        else:
            return "unknown"

    def _calculate_engagement_metrics(self, platform: str, results: List[Dict]) -> Dict:
        """Calculate engagement metrics for a platform"""
        metrics = {}
        
        if platform == "youtube":
            # YouTube-specific engagement metrics
            video_count = len([result for result in results if result.get('content_type') == '解説動画'])
            metrics["video_count"] = video_count
            
            # Additional YouTube-specific metrics can be added here
            
        elif platform == "twitter":
            # Twitter-specific engagement metrics
            tweet_count = len(results)
            metrics["tweet_count"] = tweet_count
            
            # Additional Twitter-specific metrics can be added here
            
        elif platform == "github":
            # GitHub-specific engagement metrics
            repo_count = len(results)
            metrics["repo_count"] = repo_count
            
            if repo_count > 0:
                # Calculate average stars, forks, and other metrics
                total_stars = sum(repo.get('stars', 0) for repo in results)
                total_forks = sum(repo.get('forks', 0) for repo in results)
                total_issues = sum(repo.get('open_issues', 0) for repo in results)
                
                metrics["avg_stars"] = round(total_stars / repo_count, 2)
                metrics["avg_forks"] = round(total_forks / repo_count, 2)
                metrics["avg_issues"] = round(total_issues / repo_count, 2)
                metrics["total_stars"] = total_stars
                metrics["total_forks"] = total_forks
                metrics["total_issues"] = total_issues
                
                # Language distribution
                languages = [repo.get('language', 'Unknown') for repo in results if repo.get('language')]
                if languages:
                    from collections import Counter
                    lang_counts = Counter(languages)
                    metrics["top_languages"] = dict(lang_counts.most_common(3))
                
                # Topic analysis
                all_topics = []
                for repo in results:
                    topics = repo.get('topics', [])
                    if isinstance(topics, list):
                        all_topics.extend(topics)
                
                if all_topics:
                    from collections import Counter
                    topic_counts = Counter(all_topics)
                    metrics["top_topics"] = dict(topic_counts.most_common(5))
                
                # Repository age analysis (if created_at is available)
                recent_repos = 0
                for repo in results:
                    created_at = repo.get('created_at', '')
                    if created_at:
                        try:
                            from datetime import datetime
                            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            days_old = (datetime.now(created_date.tzinfo) - created_date).days
                            if days_old <= 30:  # Repositories created in the last 30 days
                                recent_repos += 1
                        except:
                            pass
                
                metrics["recent_repos"] = recent_repos
                metrics["recent_repos_percentage"] = round((recent_repos / repo_count) * 100, 2) if repo_count > 0 else 0
                
                # Trend analysis using new data
                trending_repos = [repo for repo in results if repo.get('is_trending', False)]
                accelerating_repos = [repo for repo in results if repo.get('is_accelerating', False)]
                
                metrics["trending_repos_count"] = len(trending_repos)
                metrics["star_acceleration_count"] = len(accelerating_repos)
                
                # Top trending repositories by trend score
                top_trending = sorted(results, key=lambda x: x.get('trend_score', 0), reverse=True)[:5]
                metrics["top_trending_repos"] = [
                    {
                        'name': repo.get('name', ''),
                        'owner': repo.get('owner', ''),
                        'stars': repo.get('stars', 0),
                        'trend_score': repo.get('trend_score', 0),
                        'star_rate': repo.get('star_rate', 0),
                        'days_old': repo.get('days_old', 0),
                        'url': repo.get('url', '')
                    }
                    for repo in top_trending
                ]
                
                # Top star acceleration projects
                top_acceleration = sorted(results, key=lambda x: x.get('star_rate', 0), reverse=True)[:5]
                metrics["top_star_acceleration"] = [
                    {
                        'name': repo.get('name', ''),
                        'owner': repo.get('owner', ''),
                        'stars': repo.get('stars', 0),
                        'star_rate': repo.get('star_rate', 0),
                        'days_old': repo.get('days_old', 0),
                        'url': repo.get('url', '')
                    }
                    for repo in top_acceleration
                ]
                
                # Average trend score
                avg_trend_score = sum(repo.get('trend_score', 0) for repo in results) / repo_count
                metrics["avg_trend_score"] = round(avg_trend_score, 2)
        
        elif platform == "reddit":
            # Reddit-specific engagement metrics
            post_count = len(results)
            metrics["post_count"] = post_count
            
            # Additional Reddit-specific metrics can be added here
            
        elif platform == "web":
            # Web-specific engagement metrics
            search_count = len(results)
            metrics["search_count"] = search_count
            
            # Additional Web-specific metrics can be added here
            
        elif platform == "arxiv":
            # Arxiv-specific engagement metrics
            paper_count = len(results)
            metrics["paper_count"] = paper_count
            
            # Additional Arxiv-specific metrics can be added here
            
        elif platform == "hackernews":
            # Hacker News-specific engagement metrics
            story_count = len(results)
            metrics["story_count"] = story_count
            
            # Additional Hacker News-specific metrics can be added here
            
        elif platform == "producthunt":
            # Product Hunt-specific engagement metrics
            product_count = len(results)
            metrics["product_count"] = product_count
            
            # Additional Product Hunt-specific metrics can be added here
            
        elif platform == "linkedin":
            # LinkedIn-specific engagement metrics
            post_count = len(results)
            metrics["post_count"] = post_count
            
            # Additional LinkedIn-specific metrics can be added here
            
        return metrics

    def _calculate_trend_score(self, stars: int, days_old: int, star_rate: float) -> float:
        """Calculate a comprehensive trend score for GitHub repositories"""
        if days_old <= 0:
            return 0.0
        
        # Base score from star rate
        base_score = min(star_rate * 10, 50)  # Cap at 50 points
        
        # Bonus for high total stars
        star_bonus = min(stars / 100, 20)  # Up to 20 points for high star count
        
        # Recency bonus (newer repos get higher scores)
        recency_bonus = max(0, (365 - days_old) / 365 * 30)  # Up to 30 points for very recent repos
        
        # Star acceleration bonus
        acceleration_bonus = 0
        if star_rate >= 2.0:
            acceleration_bonus = 20  # High acceleration
        elif star_rate >= 1.0:
            acceleration_bonus = 10  # Moderate acceleration
        
        total_score = base_score + star_bonus + recency_bonus + acceleration_bonus
        return round(min(total_score, 100), 2)  # Cap at 100

    def _calculate_github_trend_metrics(self, stars: int, created_at: str) -> Tuple[float, int, bool, bool]:
        """Calculate GitHub repository trend metrics"""
        if not created_at:
            return (0.0, 0, False, False)
        
        try:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            days_old = (datetime.now(created_date.tzinfo) - created_date).days
            
            if days_old <= 0:
                return (0.0, 0, False, False)
            
            star_rate = stars / days_old
            
            is_trending = (stars >= 100 and days_old <= 365)
            is_accelerating = (star_rate >= 1.0 and stars >= 50)
            
            return (star_rate, days_old, is_trending, is_accelerating)
        except Exception:
            # Return default values if date parsing fails
            return (0.0, 0, False, False)

async def main():
    researcher = AITrendResearcher()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler():
        print("\n🛑 Received shutdown signal - forcing cleanup...")
        # Force exit after brief cleanup attempt
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
        # Properly close MCP clients
        try:
            await researcher._close_all_mcp_clients()
        except Exception:
            # Suppress exceptions during final cleanup
            pass

async def force_cleanup_and_exit(researcher):
    """Force exit after timeout"""
    print("⚠ Force exiting...")
    try:
        await researcher._close_all_mcp_clients()
    except Exception:
        pass
    import os
    os._exit(1)

if __name__ == "__main__":
    asyncio.run(main())