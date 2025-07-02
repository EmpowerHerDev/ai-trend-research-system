from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class BasePlatformHandler(ABC):
    """Base class for platform-specific research handlers"""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
    
    @abstractmethod
    async def research_keyword(self, client, keyword: str, config: Dict) -> Dict[str, Any]:
        """Research a keyword on the platform"""
        pass
    
    @abstractmethod
    def process_response(self, response: Any, keyword: str) -> Dict[str, Any]:
        """Process the platform response into standardized format"""
        pass
    
    def create_error_result(self, keyword: str, error: str) -> Dict[str, Any]:
        """Create standardized error result"""
        return {
            "platform": self.platform_name,
            "keyword": keyword,
            "timestamp": datetime.now().isoformat(),
            "results": [],
            "new_keywords": [],
            "sentiment_score": 0.0,
            "engagement_metrics": {},
            "error": error
        }


class YouTubeHandler(BasePlatformHandler):
    """YouTube platform research handler"""
    
    def __init__(self):
        super().__init__("youtube")
    
    async def research_keyword(self, client, keyword: str, config: Dict) -> Dict[str, Any]:
        """Research keyword on YouTube"""
        try:
            params = {
                "query": keyword,
                "order": "relevance",
                "type": "video",
                "max_results": 15
            }
            
            tool_name = config["tools"][0]
            response = await client.call_tool(tool_name, params)
            return self.process_response(response, keyword)
            
        except Exception as e:
            return self.create_error_result(keyword, str(e))
    
    def process_response(self, response: Any, keyword: str) -> Dict[str, Any]:
        """Process YouTube response"""
        results = []
        data = self._extract_data_from_response(response)
        
        videos = data if isinstance(data, list) else data.get('videos', data.get('items', []))
        
        for video in videos:
            snippet = video.get('snippet', {})
            video_id = video.get('id', {}).get('videoId', '')
            
            content_type = self._classify_content(
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
        
        return {
            "platform": self.platform_name,
            "keyword": keyword,
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "new_keywords": [],
            "sentiment_score": 0.0,
            "engagement_metrics": self._calculate_engagement_metrics(results)
        }
    
    def _extract_data_from_response(self, response: Any) -> Any:
        """Extract data from various response formats"""
        if isinstance(response, list) and len(response) > 0:
            first_item = response[0]
            if hasattr(first_item, 'text'):
                try:
                    return json.loads(first_item.text)
                except (json.JSONDecodeError, AttributeError):
                    return {}
            else:
                return response
        elif hasattr(response, 'content') and response.content:
            return response.content
        elif isinstance(response, dict):
            return response
        else:
            return {}
    
    def _classify_content(self, title: str, description: str) -> str:
        """Classify YouTube content type"""
        text = (title + ' ' + description).lower()
        
        if any(keyword in text for keyword in ['解説', '説明', '入門', '基礎', '学習', 'チュートリアル']):
            return "解説動画"
        elif any(keyword in text for keyword in ['デモ', 'デモンストレーション', '実演', '動作確認', 'サンプル']):
            return "デモ"
        elif any(keyword in text for keyword in ['カンファレンス', 'セミナー', '講演', '発表', 'conference', 'talk']):
            return "カンファレンス"
        elif any(keyword in text for keyword in ['ニュース', '最新', 'アップデート', 'リリース']):
            return "ニュース"
        elif any(keyword in text for keyword in ['レビュー', '比較', '検証', '評価']):
            return "レビュー"
        else:
            return "その他"
    
    def _detect_language(self, text: str) -> str:
        """Detect language of the text"""
        japanese_chars = set('あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン')
        
        if any(char in japanese_chars for char in text):
            return "ja"
        elif any(char.isascii() for char in text):
            return "en"
        else:
            return "unknown"
    
    def _calculate_engagement_metrics(self, results: List[Dict]) -> Dict:
        """Calculate YouTube engagement metrics"""
        return {
            "video_count": len([r for r in results if r.get('content_type') == '解説動画']),
            "total_videos": len(results)
        }


class GitHubHandler(BasePlatformHandler):
    """GitHub platform research handler"""
    
    def __init__(self):
        super().__init__("github")
    
    async def research_keyword(self, client, keyword: str, config: Dict) -> Dict[str, Any]:
        """Research keyword on GitHub"""
        try:
            params = {
                "query": f"{keyword} followers:>1000 stars:>50",
                "sort": "stars",
                "order": "desc",
                "per_page": 10
            }
            
            tool_name = "search_repositories"
            response = await client.call_tool(tool_name, params)
            return self.process_response(response, keyword)
            
        except Exception as e:
            return self.create_error_result(keyword, str(e))
    
    def process_response(self, response: Any, keyword: str) -> Dict[str, Any]:
        """Process GitHub response"""
        results = []
        repos = self._extract_repositories(response)
        
        for repo in repos:
            if isinstance(repo, dict):
                owner_data = repo.get('owner', {})
                owner = owner_data.get('login', '') if isinstance(owner_data, dict) else str(owner_data)
                
                stars = repo.get('stargazers_count', repo.get('stars', 0))
                created_at = repo.get('created_at', '')
                
                star_rate, days_old, is_trending, is_accelerating = self._calculate_trend_metrics(stars, created_at)
                
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
                    'updated_at': repo.get('updated_at', ''),
                    'size': repo.get('size', 0),
                    'open_issues': repo.get('open_issues_count', 0),
                    'star_rate': round(star_rate, 2),
                    'days_old': days_old,
                    'is_trending': is_trending,
                    'is_accelerating': is_accelerating,
                    'trend_score': self._calculate_trend_score(stars, days_old, star_rate)
                })
        
        return {
            "platform": self.platform_name,
            "keyword": keyword,
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "new_keywords": [],
            "sentiment_score": 0.0,
            "engagement_metrics": self._calculate_engagement_metrics(results)
        }
    
    def _extract_repositories(self, response: Any) -> List[Dict]:
        """Extract repositories from various response formats"""
        repos = []
        
        if isinstance(response, list):
            repos = response
        elif isinstance(response, dict):
            repos = response.get('repositories', response.get('items', response.get('data', [])))
        
        if not repos and isinstance(response, list) and len(response) > 0:
            first_item = response[0]
            if hasattr(first_item, 'text'):
                try:
                    parsed_data = json.loads(first_item.text)
                    if isinstance(parsed_data, list):
                        repos = parsed_data
                    elif isinstance(parsed_data, dict):
                        repos = parsed_data.get('repositories', parsed_data.get('items', parsed_data.get('data', [])))
                except (json.JSONDecodeError, AttributeError):
                    repos = self._parse_github_text_response(first_item.text)
        
        return repos
    
    def _parse_github_text_response(self, text: str) -> List[Dict]:
        """Parse GitHub repository results from text format"""
        results = []
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
        
        return results
    
    def _calculate_trend_metrics(self, stars: int, created_at: str) -> tuple:
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
            return (0.0, 0, False, False)
    
    def _calculate_trend_score(self, stars: int, days_old: int, star_rate: float) -> float:
        """Calculate comprehensive trend score"""
        if days_old <= 0:
            return 0.0
        
        base_score = min(star_rate * 10, 50)
        star_bonus = min(stars / 100, 20)
        recency_bonus = max(0, (365 - days_old) / 365 * 30)
        
        acceleration_bonus = 0
        if star_rate >= 2.0:
            acceleration_bonus = 20
        elif star_rate >= 1.0:
            acceleration_bonus = 10
        
        total_score = base_score + star_bonus + recency_bonus + acceleration_bonus
        return round(min(total_score, 100), 2)
    
    def _calculate_engagement_metrics(self, results: List[Dict]) -> Dict:
        """Calculate GitHub engagement metrics"""
        if not results:
            return {"repo_count": 0}
        
        repo_count = len(results)
        total_stars = sum(repo.get('stars', 0) for repo in results)
        total_forks = sum(repo.get('forks', 0) for repo in results)
        
        metrics = {
            "repo_count": repo_count,
            "avg_stars": round(total_stars / repo_count, 2) if repo_count > 0 else 0,
            "avg_forks": round(total_forks / repo_count, 2) if repo_count > 0 else 0,
            "total_stars": total_stars,
            "total_forks": total_forks
        }
        
        # Language distribution
        languages = [repo.get('language', 'Unknown') for repo in results if repo.get('language')]
        if languages:
            from collections import Counter
            lang_counts = Counter(languages)
            metrics["top_languages"] = dict(lang_counts.most_common(3))
        
        # Trending analysis
        trending_repos = [repo for repo in results if repo.get('is_trending', False)]
        metrics["trending_repos_count"] = len(trending_repos)
        
        return metrics


class WebHandler(BasePlatformHandler):
    """Web search platform research handler"""
    
    def __init__(self):
        super().__init__("web")
    
    async def research_keyword(self, client, keyword: str, config: Dict) -> Dict[str, Any]:
        """Research keyword on web"""
        try:
            params = {
                "query": f"{keyword} 日本語",
                "language": "ja",
                "region": "jp",
                "max_results": 10
            }
            
            tool_name = config["tools"][0]
            response = await client.call_tool(tool_name, params)
            return self.process_response(response, keyword)
            
        except Exception as e:
            return self.create_error_result(keyword, str(e))
    
    def process_response(self, response: Any, keyword: str) -> Dict[str, Any]:
        """Process web search response"""
        results = self._parse_web_results(response)
        
        return {
            "platform": self.platform_name,
            "keyword": keyword,
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "new_keywords": [],
            "sentiment_score": 0.0,
            "engagement_metrics": {"search_count": len(results)}
        }
    
    def _parse_web_results(self, response: Any) -> List[Dict]:
        """Parse web search results from various formats"""
        results = []
        
        # Handle TextContent objects
        if isinstance(response, list) and len(response) > 0:
            first_item = response[0]
            if hasattr(first_item, 'text'):
                return self._parse_web_search_text(first_item.text)
        
        # Handle structured data
        if isinstance(response, dict):
            if 'results' in response or 'items' in response:
                web_results = response.get('results', response.get('items', []))
                for result in web_results:
                    results.append({
                        'title': result.get('title', ''),
                        'snippet': result.get('snippet', result.get('description', '')),
                        'url': result.get('url', result.get('link', '')),
                        'source': result.get('source', '')
                    })
        
        return results
    
    def _parse_web_search_text(self, text: str) -> List[Dict]:
        """Parse web search results from text format"""
        results = []
        sections = text.split('\n\n')
        
        for section in sections:
            if not section.strip():
                continue
                
            lines = section.strip().split('\n')
            if len(lines) < 2:
                continue
            
            title_line = lines[0]
            title = title_line[7:] if title_line.startswith('Title: ') else title_line
            
            url = ""
            if len(lines) > 1 and lines[1].startswith('URL: '):
                url = lines[1][5:]
            
            description = ""
            if len(lines) > 2 and lines[2].startswith('Description: '):
                description = lines[2][13:]
                for line in lines[3:]:
                    if line.strip() and not line.startswith('URL: '):
                        description += " " + line.strip()
            
            if title and url:
                results.append({
                    'title': title,
                    'snippet': description,
                    'url': url,
                    'source': self._extract_domain_from_url(url)
                })
        
        return results
    
    def _extract_domain_from_url(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return ""


class PlatformHandlerFactory:
    """Factory for creating platform handlers"""
    
    @staticmethod
    def create_handler(platform: str) -> BasePlatformHandler:
        """Create appropriate handler for platform"""
        handlers = {
            "youtube": YouTubeHandler,
            "github": GitHubHandler,
            "web": WebHandler
        }
        
        handler_class = handlers.get(platform)
        if handler_class:
            return handler_class()
        else:
            raise ValueError(f"No handler available for platform: {platform}")