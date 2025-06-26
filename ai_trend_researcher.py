import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Any
from anthropic import Anthropic
from mcp import Client
from keyword_manager import KeywordManager

class AITrendResearcher:
    def __init__(self):
        self.keyword_manager = KeywordManager()
        self.reports_dir = "reports"
        self.claude_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.mcp_client = None
        self.platforms = [
            "twitter", "youtube", "web", "github", "reddit", 
            "linkedin", "arxiv", "hackernews", "producthunt"
        ]
    
    async def research_platform(self, platform: str, keyword: str) -> Dict[str, Any]:
        """Research a specific platform for a keyword"""
        
        if platform.lower() == "youtube":
            return await self._research_youtube(keyword)
        
        # Mock data for other platforms
        return {
            "platform": platform,
            "keyword": keyword,
            "timestamp": datetime.now().isoformat(),
            "results": [],
            "new_keywords": [],
            "sentiment_score": 0.0,
            "engagement_metrics": {}
        }
    
    async def connect_mcp(self):
        """Connect to YouTube MCP server"""
        if not self.mcp_client:
            try:
                self.mcp_client = Client()
                await self.mcp_client.connect_to_server("youtube-mcp-server")
                print("✓ Connected to YouTube MCP server")
            except Exception as e:
                print(f"✗ Failed to connect to YouTube MCP server: {e}")
                self.mcp_client = None
    
    async def _research_youtube(self, keyword: str) -> Dict[str, Any]:
        """Research YouTube via MCP server"""
        if not self.mcp_client:
            await self.connect_mcp()
        
        if not self.mcp_client:
            print("YouTube MCP server not available, using fallback")
            return {
                "platform": "youtube",
                "keyword": keyword,
                "timestamp": datetime.now().isoformat(),
                "results": [],
                "new_keywords": [],
                "sentiment_score": 0.0,
                "engagement_metrics": {},
                "error": "MCP server not available"
            }
        
        try:
            # Call YouTube MCP server search tool
            response = await self.mcp_client.call_tool(
                "search_videos",
                {
                    "query": keyword,
                    "max_results": 10,
                    "order": "relevance"
                }
            )
            return self._process_mcp_youtube_response(response, keyword)
            
        except Exception as e:
            print(f"YouTube MCP error: {e}")
            return {
                "platform": "youtube",
                "keyword": keyword,
                "timestamp": datetime.now().isoformat(),
                "results": [],
                "new_keywords": [],
                "sentiment_score": 0.0,
                "engagement_metrics": {},
                "error": str(e)
            }
    
    def _process_mcp_youtube_response(self, response: Any, keyword: str) -> Dict[str, Any]:
        """Process YouTube MCP server response"""
        results = []
        
        # Process MCP response format
        if hasattr(response, 'content') and response.content:
            videos = response.content.get('videos', [])
            for video in videos:
                results.append({
                    'title': video.get('title', ''),
                    'description': video.get('description', ''),
                    'published_at': video.get('published_at', ''),
                    'channel': video.get('channel_title', ''),
                    'video_id': video.get('video_id', ''),
                    'view_count': video.get('view_count', 0),
                    'duration': video.get('duration', '')
                })
        elif isinstance(response, dict):
            # Handle direct dict response
            videos = response.get('videos', response.get('items', []))
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
        
        return {
            "platform": "youtube",
            "keyword": keyword,
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "new_keywords": [],
            "sentiment_score": 0.0,
            "engagement_metrics": {
                "total_videos": len(results),
                "total_views": sum(r.get('view_count', 0) for r in results)
            }
        }
    
    async def extract_new_keywords(self, research_data: List[Dict]) -> List[str]:
        """Extract new keywords using Claude AI"""
        if not research_data or not self.claude_client:
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
                        'description': result.get('description', '')[:200]  # Limit description length
                    })
        
        if not content_summary:
            return []
        
        try:
            prompt = f"""Analyze this AI trend research data and extract 5-10 new trending keywords related to AI, machine learning, or technology.
            
Data: {json.dumps(content_summary, indent=2)}
            
Return only a JSON array of keywords, like: ["keyword1", "keyword2", "keyword3"]
            Focus on: AI tools, frameworks, companies, techniques, or emerging technologies."""
            
            response = await self._call_claude(prompt)
            return self._parse_keywords_from_response(response)
            
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
        
        # Initialize MCP connections
        await self.connect_mcp()
        
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

async def main():
    researcher = AITrendResearcher()
    await researcher.run_daily_research()

if __name__ == "__main__":
    asyncio.run(main())