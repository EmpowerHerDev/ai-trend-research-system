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


class ArxivHandler(BasePlatformHandler):
    """arXiv platform research handler"""
    
    def __init__(self, claude_client=None):
        super().__init__("arxiv")
        self.claude_client = claude_client
        print(f"🔍 ArxivHandler initialized with Claude client: {claude_client is not None}")
    
    async def research_keyword(self, client, keyword: str, config: Dict) -> Dict[str, Any]:
        """Research keyword on arXiv"""
        try:
            # Translate Japanese keywords to English using Claude AI
            english_query = self._translate_keyword_with_claude(keyword)
            
            # Try primary search
            params = {
                "query": english_query,
                "max_results": 10
            }
            
            tool_name = "search_arxiv"  # Fixed: use correct tool name from config
            print(f"🔍 Calling arXiv tool '{tool_name}' with params: {params}")
            print(f"🔍 Original keyword: '{keyword}' -> English query: '{english_query}'")
            response = await client.call_tool(tool_name, params)
            print(f"📄 arXiv raw response type: {type(response)}")
            print(f"📄 arXiv raw response: {response}")
            
            # Check if we got results
            papers = self._extract_papers(response)
            if not papers:
                # Try fallback search with broader terms
                fallback_query = self._get_fallback_query_with_claude(english_query)
                if fallback_query != english_query:
                    print(f"🔍 No results found, trying fallback query: '{fallback_query}'")
                    fallback_params = {
                        "query": fallback_query,
                        "max_results": 10
                    }
                    fallback_response = await client.call_tool(tool_name, fallback_params)
                    print(f"📄 Fallback response: {fallback_response}")
                    
                    # Use fallback response if it has results
                    fallback_papers = self._extract_papers(fallback_response)
                    if fallback_papers:
                        response = fallback_response
                        print(f"📄 Using fallback results: {len(fallback_papers)} papers found")
            
            return self.process_response(response, keyword)
            
        except Exception as e:
            print(f"❌ Error in arXiv research: {e}")
            return self.create_error_result(keyword, str(e))
    
    def _translate_keyword_with_claude(self, keyword: str) -> str:
        """Translate Japanese keyword to English using Claude AI"""
        print(f"🔍 Claude client available: {self.claude_client is not None}")
        if not self.claude_client:
            print("⚠️ Claude client not available, using fallback translation")
            return self._translate_keyword_to_english_fallback(keyword)
        
        try:
            prompt = f"""
あなたはAI研究分野の専門家です。以下の日本語のキーワードを、arXivで検索するのに適した英語のキーワードに翻訳してください。

日本語キーワード: {keyword}

以下の点に注意してください：
1. AI研究分野で一般的に使用される英語の専門用語を使用
2. arXivで検索する際に効果的なキーワードを選択
3. 複数の関連キーワードがある場合は、最も適切なものを1つ選択
4. 回答は英語のキーワードのみで、説明は不要

英語キーワード:"""

            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=50,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            english_keyword = response.content[0].text.strip()
            print(f"🤖 Claude translated '{keyword}' -> '{english_keyword}'")
            return english_keyword
            
        except Exception as e:
            print(f"❌ Claude translation error: {e}, using fallback")
            return keyword
    
    def _get_fallback_query_with_claude(self, query: str) -> str:
        """Get a broader fallback query using Claude AI"""
        if not self.claude_client:
            return self._get_fallback_query_fallback(query)
        
        try:
            prompt = f"""
あなたはAI研究分野の専門家です。以下の英語のキーワードでarXiv検索を行ったが結果が見つからなかった場合、より一般的で広範囲な検索キーワードを提案してください。

元のキーワード: {query}

以下の点に注意してください：
1. より一般的で広範囲なAI関連のキーワードを提案
2. 元のキーワードより具体的でない、より包括的なキーワードを選択
3. arXivで検索する際に効果的なキーワードを選択
4. 回答は英語のキーワードのみで、説明は不要

提案するキーワード:"""

            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=50,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            fallback_keyword = response.content[0].text.strip()
            print(f"🤖 Claude suggested fallback: '{query}' -> '{fallback_keyword}'")
            return fallback_keyword
            
        except Exception as e:
            print(f"❌ Claude fallback suggestion error: {e}, using fallback")
            return query
    
    def process_response(self, response: Any, keyword: str) -> Dict[str, Any]:
        """Process arXiv response"""
        results = []
        papers = self._extract_papers(response)
        
        for paper in papers:
            if isinstance(paper, dict):
                # Extract authors
                authors = paper.get('authors', [])
                if isinstance(authors, str):
                    authors = [author.strip() for author in authors.split(',')]
                
                # Calculate metrics
                published_date = paper.get('published', paper.get('published_date', ''))
                days_old, is_recent = self._calculate_time_metrics(published_date)
                
                results.append({
                    'title': paper.get('title', ''),
                    'abstract': paper.get('abstract', ''),
                    'authors': authors,
                    'published_date': published_date,
                    'arxiv_id': paper.get('id', paper.get('arxiv_id', '')),
                    'url': paper.get('url', paper.get('pdf_url', '')),
                    'categories': paper.get('categories', []),
                    'summary': paper.get('summary', ''),
                    'days_old': days_old,
                    'is_recent': is_recent,
                    'citation_count': paper.get('citation_count', 0),
                    'download_count': paper.get('download_count', 0),
                    'trend_score': self._calculate_trend_score(paper)
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
    
    def _extract_papers(self, response: Any) -> List[Dict]:
        """Extract papers from various response formats"""
        print(f"🔍 Extracting papers from response type: {type(response)}")
        papers = []
        
        # Handle None or empty response
        if not response:
            print("📄 Response is empty or None")
            return papers
        
        # Handle string response (might be JSON string)
        if isinstance(response, str):
            print(f"📄 Response is string: {response[:200]}...")
            # Check if it's Chinese format first
            if "找到" in response and "篇相关论文" in response:
                print(f"📄 Detected Chinese format, parsing directly")
                return self._parse_chinese_arxiv_format(response)
            try:
                parsed_data = json.loads(response)
                return self._extract_papers(parsed_data)
            except json.JSONDecodeError:
                # Try to parse as text format
                return self._parse_arxiv_text_response(response)
        
        # Handle list response
        if isinstance(response, list):
            print(f"📄 Response is list with {len(response)} items")
            if len(response) > 0:
                first_item = response[0]
                print(f"📄 First item type: {type(first_item)}")
                
                # Handle TextContent objects
                if hasattr(first_item, 'text'):
                    text_content = first_item.text
                    print(f"📄 First item has text attribute: {text_content[:200]}...")
                    
                    # Check if it's Chinese format first
                    if "找到" in text_content and "篇相关论文" in text_content:
                        print(f"📄 Detected Chinese format in TextContent, parsing directly")
                        return self._parse_chinese_arxiv_format(text_content)
                    
                    # Try JSON parsing only if it doesn't look like Chinese format
                    if text_content.strip().startswith('{') or text_content.strip().startswith('['):
                        try:
                            parsed_data = json.loads(text_content)
                            print(f"📄 Parsed JSON data type: {type(parsed_data)}")
                            return self._extract_papers(parsed_data)
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON parsing error: {e}")
                            return self._parse_arxiv_text_response(text_content)
                    else:
                        # Not JSON format, parse as text
                        print(f"📄 Not JSON format, parsing as text")
                        return self._parse_arxiv_text_response(text_content)
                else:
                    # Direct list of paper objects
                    papers = response
        
        # Handle dict response
        elif isinstance(response, dict):
            print(f"📄 Response is dict with keys: {list(response.keys())}")
            # Try different possible keys for papers
            for key in ['papers', 'entries', 'data', 'results', 'items']:
                if key in response:
                    papers = response[key]
                    print(f"📄 Found papers under key '{key}': {len(papers)} items")
                    break
            
            # If no papers found, treat the whole response as a single paper
            if not papers and any(key in response for key in ['title', 'abstract', 'authors']):
                papers = [response]
                print("📄 Treating response as single paper")
        
        print(f"📄 Extracted {len(papers)} papers")
        return papers
    
    def _parse_arxiv_text_response(self, text: str) -> List[Dict]:
        """Parse arXiv paper results from text format"""
        results = []
        
        # Check if response indicates no results found
        no_results_indicators = [
            "找到 0 篇相关论文",  # Chinese: Found 0 related papers
            "0 篇相关论文",      # Chinese: 0 related papers
            "no results found",  # English
            "0 results",         # English
            "no papers found",   # English
            "0 papers"           # English
        ]
        
        if any(indicator in text for indicator in no_results_indicators):
            print(f"📄 No papers found in response: {text}")
            return results
        
        # Parse Chinese format: "找到 X 篇相关论文（总计 Y 篇）："
        if "找到" in text and "篇相关论文" in text:
            print(f"📄 Parsing Chinese format response")
            return self._parse_chinese_arxiv_format(text)
        
        # Parse English format
        sections = text.split('\n\n')
        
        for section in sections:
            if not section.strip():
                continue
                
            lines = section.strip().split('\n')
            if len(lines) < 2:
                continue
            
            paper_info = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('Title: '):
                    paper_info['title'] = line[7:]
                elif line.startswith('Authors: '):
                    authors_str = line[9:]
                    paper_info['authors'] = [author.strip() for author in authors_str.split(',')]
                elif line.startswith('Abstract: '):
                    paper_info['abstract'] = line[10:]
                elif line.startswith('Published: '):
                    paper_info['published_date'] = line[11:]
                elif line.startswith('arXiv ID: '):
                    paper_info['arxiv_id'] = line[10:]
                elif line.startswith('URL: '):
                    paper_info['url'] = line[5:]
                elif line.startswith('Categories: '):
                    categories_str = line[12:]
                    paper_info['categories'] = [cat.strip() for cat in categories_str.split(',')]
            
            if paper_info.get('title') and paper_info.get('arxiv_id'):
                results.append({
                    'title': paper_info.get('title', ''),
                    'abstract': paper_info.get('abstract', ''),
                    'authors': paper_info.get('authors', []),
                    'published_date': paper_info.get('published_date', ''),
                    'arxiv_id': paper_info.get('arxiv_id', ''),
                    'url': paper_info.get('url', ''),
                    'categories': paper_info.get('categories', []),
                    'summary': paper_info.get('abstract', ''),
                    'citation_count': 0,
                    'download_count': 0
                })
        
        return results
    
    def _parse_chinese_arxiv_format(self, text: str) -> List[Dict]:
        """Parse Chinese format arXiv response"""
        results = []
        
        print(f"📄 Starting Chinese format parsing for text length: {len(text)}")
        
        # Split by numbered entries (1. **Title**, 2. **Title**, etc.)
        import re
        paper_sections = re.split(r'\n\n\d+\.\s+\*\*', text)
        
        print(f"📄 Found {len(paper_sections)} sections after splitting")
        
        # If regex splitting didn't work well, try alternative approach
        if len(paper_sections) <= 1:
            print(f"📄 Regex splitting didn't work, trying alternative parsing")
            return self._parse_chinese_arxiv_alternative(text)
        
        # Skip the first section (header with "找到 X 篇相关论文")
        for i, section in enumerate(paper_sections[1:], 1):
            if not section.strip():
                continue
            
            try:
                print(f"📄 Processing section {i}")
                
                # Extract title (everything before the first newline)
                lines = section.strip().split('\n')
                title = lines[0].strip()
                
                # Clean up title by removing trailing **
                if title.endswith('**'):
                    title = title[:-2]
                
                paper_info = {
                    'title': title,
                    'abstract': '',
                    'authors': [],
                    'published_date': '',
                    'arxiv_id': '',
                    'url': '',
                    'categories': [],
                    'summary': '',
                    'citation_count': 0,
                    'download_count': 0
                }
                
                # Parse the rest of the lines
                for line in lines[1:]:
                    line = line.strip()
                    if line.startswith('ID: '):
                        paper_info['arxiv_id'] = line[4:]
                    elif line.startswith('发布日期: '):
                        paper_info['published_date'] = line[6:]
                    elif line.startswith('作者: '):
                        authors_str = line[4:]
                        paper_info['authors'] = [author.strip() for author in authors_str.split(',')]
                    elif line.startswith('摘要: '):
                        paper_info['abstract'] = line[4:]
                        paper_info['summary'] = line[4:]
                    elif line.startswith('URL: '):
                        paper_info['url'] = line[5:]
                
                if paper_info['title'] and paper_info['arxiv_id']:
                    results.append(paper_info)
                    print(f"📄 Successfully parsed paper: {paper_info['title'][:50]}...")
                else:
                    print(f"❌ Skipping paper due to missing title or arxiv_id")
                
            except Exception as e:
                print(f"❌ Error parsing paper section {i}: {e}")
                continue
        
        print(f"📄 Successfully parsed {len(results)} papers from Chinese format")
        return results
    
    def _parse_chinese_arxiv_alternative(self, text: str) -> List[Dict]:
        """Alternative parsing method for Chinese arXiv format"""
        results = []
        
        # Look for patterns like "**Title**" followed by metadata
        import re
        paper_pattern = r'\*\*(.*?)\*\*\s*\n\s*ID:\s*([^\n]+)\s*\n\s*发布日期:\s*([^\n]+)\s*\n\s*作者:\s*([^\n]+)\s*\n\s*摘要:\s*([^\n]+)\s*\n\s*URL:\s*([^\n]+)'
        
        matches = re.findall(paper_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                title, arxiv_id, published_date, authors_str, abstract, url = match
                
                # Clean up title
                if title.endswith('**'):
                    title = title[:-2]
                
                # Parse authors
                authors = [author.strip() for author in authors_str.split(',')]
                
                paper_info = {
                    'title': title.strip(),
                    'abstract': abstract.strip(),
                    'authors': authors,
                    'published_date': published_date.strip(),
                    'arxiv_id': arxiv_id.strip(),
                    'url': url.strip(),
                    'categories': [],
                    'summary': abstract.strip(),
                    'citation_count': 0,
                    'download_count': 0
                }
                
                if paper_info['title'] and paper_info['arxiv_id']:
                    results.append(paper_info)
                    print(f"📄 Alternative parsing: {paper_info['title'][:50]}...")
                
            except Exception as e:
                print(f"❌ Error in alternative parsing: {e}")
                continue
        
        print(f"📄 Alternative parsing found {len(results)} papers")
        return results
    
    def _calculate_time_metrics(self, published_date: str) -> tuple:
        """Calculate time-based metrics for papers"""
        if not published_date:
            return (0, False)
        
        try:
            # Handle various date formats including Chinese format with timezone
            if 'T' in published_date and 'Z' in published_date:
                # Format: "2025-02-16T23:19:44Z"
                from datetime import datetime
                pub_date = datetime.strptime(published_date, '%Y-%m-%dT%H:%M:%SZ')
                days_old = (datetime.now() - pub_date).days
                is_recent = days_old <= 365  # Papers published within a year
                return (days_old, is_recent)
            elif 'T' in published_date:
                # Format: "2025-02-16T23:19:44"
                published_date = published_date.split('T')[0]
            
            from datetime import datetime
            pub_date = datetime.strptime(published_date, '%Y-%m-%d')
            days_old = (datetime.now() - pub_date).days
            is_recent = days_old <= 365  # Papers published within a year
            
            return (days_old, is_recent)
        except Exception as e:
            print(f"❌ Error parsing date '{published_date}': {e}")
            return (0, False)
    
    def _calculate_trend_score(self, paper: Dict) -> float:
        """Calculate trend score for a paper"""
        score = 0.0
        
        # Recency bonus
        days_old = paper.get('days_old', 0)
        if days_old <= 30:
            score += 30
        elif days_old <= 90:
            score += 20
        elif days_old <= 365:
            score += 10
        
        # Citation bonus
        citations = paper.get('citation_count', 0)
        if citations > 100:
            score += 25
        elif citations > 50:
            score += 15
        elif citations > 10:
            score += 5
        
        # Category relevance bonus
        categories = paper.get('categories', [])
        ai_categories = ['cs.AI', 'cs.LG', 'cs.CL', 'cs.CV', 'cs.NE', 'stat.ML']
        if any(cat in categories for cat in ai_categories):
            score += 15
        
        return round(min(score, 100), 2)
    
    def _calculate_engagement_metrics(self, results: List[Dict]) -> Dict:
        """Calculate arXiv engagement metrics"""
        if not results:
            return {"paper_count": 0}
        
        paper_count = len(results)
        recent_papers = len([p for p in results if p.get('is_recent', False)])
        total_citations = sum(p.get('citation_count', 0) for p in results)
        
        metrics = {
            "paper_count": paper_count,
            "recent_papers": recent_papers,
            "avg_citations": round(total_citations / paper_count, 2) if paper_count > 0 else 0,
            "total_citations": total_citations
        }
        
        # Category distribution
        all_categories = []
        for paper in results:
            all_categories.extend(paper.get('categories', []))
        
        if all_categories:
            from collections import Counter
            cat_counts = Counter(all_categories)
            metrics["top_categories"] = dict(cat_counts.most_common(5))
        
        # Author analysis
        all_authors = []
        for paper in results:
            all_authors.extend(paper.get('authors', []))
        
        if all_authors:
            from collections import Counter
            author_counts = Counter(all_authors)
            metrics["top_authors"] = dict(author_counts.most_common(3))
        
        return metrics


class HackerNewsHandler(BasePlatformHandler):
    """HackerNews platform research handler"""
    
    def __init__(self, claude_client=None):
        super().__init__("hackernews")
        self.claude_client = claude_client
        print(f"🔍 HackerNewsHandler initialized with Claude client: {claude_client is not None}")
    
    async def research_keyword(self, client, keyword: str, config: Dict) -> Dict[str, Any]:
        """Research keyword on HackerNews"""
        try:
            # First try to get top stories as a fallback since search might not work well
            print(f"🔍 Getting top stories from HackerNews for keyword: {keyword}")
            
            # Try to get top stories first (this is more reliable)
            try:
                top_stories_response = await client.call_tool("getStories", {"max_results": 15})
                print(f"📄 Top stories response type: {type(top_stories_response)}")
                
                # Debug: Print raw response for first few items
                if isinstance(top_stories_response, list) and len(top_stories_response) > 0:
                    first_item = top_stories_response[0]
                    if hasattr(first_item, 'text'):
                        print(f"📄 Raw response sample: {first_item.text[:500]}...")
                
                top_posts = self._extract_posts(top_stories_response)
                
                if top_posts and len(top_posts) > 0:
                    print(f"📄 Found {len(top_posts)} top stories")
                    return self.process_response(top_stories_response, keyword)
            except Exception as e:
                print(f"❌ Error getting top stories: {e}")
            
            # If top stories failed, try search with translated keyword
            print(f"🔍 Trying search for keyword: {keyword}")
            
            # Translate Japanese keyword to English using Claude API
            english_keyword = self._translate_keyword_with_claude(keyword)
            if english_keyword != keyword:
                print(f"🔍 Claude translated keyword '{keyword}' -> '{english_keyword}'")
            
            params = {
                "query": english_keyword,
                "max_results": 10
            }
            
            tool_name = "search"
            print(f"🔍 Calling HackerNews tool '{tool_name}' with params: {params}")
            response = await client.call_tool(tool_name, params)
            print(f"📄 HackerNews search response type: {type(response)}")
            
            # Check if we got meaningful results
            posts = self._extract_posts(response)
            if not posts or self._has_undefined_values(posts):
                print(f"🔍 No meaningful search results found for '{keyword}', trying broader search")
                
                # Try with broader English terms using Claude
                broader_keywords = self._get_broader_keywords_with_claude(english_keyword)
                for broader_keyword in broader_keywords:
                    print(f"🔍 Trying broader keyword: '{broader_keyword}'")
                    broader_params = {
                        "query": broader_keyword,
                        "max_results": 10
                    }
                    
                    try:
                        broader_response = await client.call_tool(tool_name, broader_params)
                        broader_posts = self._extract_posts(broader_response)
                        
                        if broader_posts and not self._has_undefined_values(broader_posts):
                            print(f"📄 Found meaningful results with broader keyword '{broader_keyword}'")
                            return self.process_response(broader_response, keyword)
                    except Exception as e:
                        print(f"❌ Error with broader keyword '{broader_keyword}': {e}")
                        continue
                
                # If all searches failed, return top stories as fallback
                print(f"🔍 All searches failed, returning top stories as fallback")
                try:
                    fallback_response = await client.call_tool("getStories", {"max_results": 15})
                    fallback_posts = self._extract_posts(fallback_response)
                    if fallback_posts and len(fallback_posts) > 0:
                        return self.process_response(fallback_response, keyword)
                except Exception as e:
                    print(f"❌ Error getting fallback top stories: {e}")
                
                return self.create_error_result(keyword, "No meaningful results found")
            
            return self.process_response(response, keyword)
            
        except Exception as e:
            print(f"❌ Error in HackerNews research: {e}")
            return self.create_error_result(keyword, str(e))
    
    def _has_undefined_values(self, posts: List[Dict]) -> bool:
        """Check if posts have undefined values indicating poor search results"""
        if not posts:
            return True
        
        # Count how many posts have undefined/missing values
        invalid_count = 0
        total_count = len(posts)
        
        for post in posts:
            if isinstance(post, dict):
                # Check if key fields are undefined or missing
                title = post.get('title', '')
                if title == 'undefined' or not title:
                    invalid_count += 1
                    continue
                
                score = post.get('score', post.get('points', 0))
                if score == 'undefined' or score is None:
                    invalid_count += 1
                    continue
                
                # If we have a valid title and score, this post is probably valid
                if title and score != 'undefined' and score is not None:
                    continue
                
                invalid_count += 1
        
        # If more than 50% of posts are invalid, consider the results poor
        invalid_ratio = invalid_count / total_count if total_count > 0 else 1.0
        print(f"📄 Invalid posts ratio: {invalid_count}/{total_count} ({invalid_ratio:.2%})")
        
        return invalid_ratio > 0.5
    
    def process_response(self, response: Any, keyword: str) -> Dict[str, Any]:
        """Process HackerNews response"""
        results = []
        posts = self._extract_posts(response)
        
        for post in posts:
            if isinstance(post, dict):
                # Calculate metrics
                score = post.get('score', post.get('points', 0))
                comments_count = post.get('descendants', post.get('comments_count', 0))
                created_time = post.get('time', post.get('created_at', ''))
                days_old, is_recent = self._calculate_time_metrics(created_time)
                
                results.append({
                    'title': post.get('title', ''),
                    'url': post.get('url', post.get('link', '')),
                    'author': post.get('by', post.get('author', '')),
                    'score': score,
                    'comments_count': comments_count,
                    'created_time': created_time,
                    'days_old': days_old,
                    'is_recent': is_recent,
                    'trend_score': self._calculate_trend_score(score, days_old, comments_count),
                    'type': post.get('type', 'story')
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
    
    def _extract_posts(self, response: Any) -> List[Dict]:
        """Extract posts from various response formats"""
        posts = []
        
        # Handle TextContent objects with text format
        if isinstance(response, list) and len(response) > 0:
            first_item = response[0]
            if hasattr(first_item, 'text'):
                text_content = first_item.text
                print(f"📄 Parsing text content: {text_content[:200]}...")
                
                # Check if it's a "No stories found" response
                if "No stories found" in text_content:
                    print(f"📄 No stories found in response")
                    return []
                
                # Try to parse the numbered list format we're seeing
                if text_content.strip().startswith('1.') or 'ID:' in text_content:
                    print(f"📄 Detected numbered format, parsing with regex")
                    return self._parse_hackernews_numbered_format(text_content)
                
                # Try JSON parsing
                try:
                    parsed_data = json.loads(text_content)
                    if isinstance(parsed_data, list):
                        posts = parsed_data
                    elif isinstance(parsed_data, dict):
                        posts = parsed_data.get('posts', parsed_data.get('stories', parsed_data.get('data', [])))
                except (json.JSONDecodeError, AttributeError) as e:
                    print(f"❌ JSON parsing error: {e}")
                    posts = self._parse_hackernews_text_response(text_content)
            else:
                # Direct list of post objects
                posts = response
        
        # Handle dict response
        elif isinstance(response, dict):
            posts = response.get('posts', response.get('stories', response.get('data', [])))
        
        return posts
    
    def _parse_hackernews_numbered_format(self, text: str) -> List[Dict]:
        """Parse the numbered format response from HackerNews server"""
        results = []
        
        # Split by numbered entries (1. title, 2. title, etc.)
        import re
        # More robust regex to handle various formats
        sections = re.split(r'\n\n\d+\.\s+', text)
        
        print(f"📄 Found {len(sections)} sections in numbered format")
        
        # Skip the first section if it's empty or just whitespace
        for i, section in enumerate(sections[1:], 1):
            if not section.strip():
                continue
            
            try:
                lines = section.strip().split('\n')
                if len(lines) < 2:
                    continue
                
                # First line is the title
                title = lines[0].strip()
                
                post_info = {
                    'title': title,
                    'url': '',
                    'author': '',
                    'score': 0,
                    'comments_count': 0,
                    'created_time': '',
                    'type': 'story'
                }
                
                # Parse the metadata lines (indented lines)
                for line in lines[1:]:
                    line = line.strip()
                    
                    # Handle ID line
                    if line.startswith('ID: '):
                        post_info['id'] = line[4:]
                    
                    # Handle URL line
                    elif line.startswith('URL: '):
                        url_part = line[5:]
                        if url_part != '(text post)':
                            post_info['url'] = url_part
                    
                    # Handle Points | Author | Comments line (various formats)
                    elif 'Points:' in line:
                        # Try to parse different formats:
                        # "Points: 906 | Author: iyaja | Comments: 123"
                        # "Points: 906 | Author: iyaja | Comment..."
                        # "Points: 906 | Author: iyaja"
                        
                        # Extract points
                        points_match = re.search(r'Points:\s*(\d+)', line)
                        if points_match:
                            try:
                                post_info['score'] = int(points_match.group(1))
                            except ValueError:
                                post_info['score'] = 0
                        
                        # Extract author
                        author_match = re.search(r'Author:\s*([^|]+)', line)
                        if author_match:
                            author_part = author_match.group(1).strip()
                            if author_part != 'undefined':
                                post_info['author'] = author_part
                        
                        # Extract comments
                        comments_match = re.search(r'Comments?:\s*(\d+)', line)
                        if comments_match:
                            try:
                                post_info['comments_count'] = int(comments_match.group(1))
                            except ValueError:
                                post_info['comments_count'] = 0
                    
                    # Handle separate metadata lines (fallback)
                    elif line.startswith('Points: '):
                        points_part = line[8:]
                        if points_part != 'undefined':
                            try:
                                post_info['score'] = int(points_part)
                            except ValueError:
                                post_info['score'] = 0
                    elif line.startswith('Author: '):
                        author_part = line[8:]
                        if author_part != 'undefined':
                            post_info['author'] = author_part
                    elif line.startswith('Comments: '):
                        comments_part = line[10:]
                        if comments_part != 'undefined':
                            try:
                                post_info['comments_count'] = int(comments_part)
                            except ValueError:
                                post_info['comments_count'] = 0
                
                # Only add if we have a meaningful title
                if post_info['title'] and post_info['title'] != 'undefined':
                    results.append(post_info)
                    print(f"📄 Parsed post: {post_info['title'][:50]}... (Score: {post_info['score']}, Author: {post_info['author']}, Comments: {post_info['comments_count']})")
                
            except Exception as e:
                print(f"❌ Error parsing section {i}: {e}")
                continue
        
        print(f"📄 Successfully parsed {len(results)} posts from numbered format")
        return results
    
    def _parse_hackernews_text_response(self, text: str) -> List[Dict]:
        """Parse HackerNews results from text format"""
        results = []
        sections = text.split('\n\n')
        
        for section in sections:
            if not section.strip():
                continue
                
            lines = section.strip().split('\n')
            if len(lines) < 2:
                continue
            
            post_info = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('Title: '):
                    post_info['title'] = line[7:]
                elif line.startswith('URL: '):
                    post_info['url'] = line[5:]
                elif line.startswith('Author: '):
                    post_info['author'] = line[8:]
                elif line.startswith('Score: '):
                    try:
                        post_info['score'] = int(line[7:])
                    except ValueError:
                        post_info['score'] = 0
                elif line.startswith('Comments: '):
                    try:
                        post_info['comments_count'] = int(line[10:])
                    except ValueError:
                        post_info['comments_count'] = 0
                elif line.startswith('Created: '):
                    post_info['created_time'] = line[9:]
            
            if post_info.get('title'):
                results.append({
                    'title': post_info.get('title', ''),
                    'url': post_info.get('url', ''),
                    'author': post_info.get('author', ''),
                    'score': post_info.get('score', 0),
                    'comments_count': post_info.get('comments_count', 0),
                    'created_time': post_info.get('created_time', ''),
                    'type': 'story'
                })
        
        return results
    
    def _calculate_time_metrics(self, created_time) -> tuple:
        """Calculate time-based metrics for posts"""
        if not created_time:
            # If no created_time is provided, assume it's recent (within last week)
            # This is a reasonable assumption for top stories from HackerNews
            return (3, True)  # 3 days old, considered recent
        
        try:
            # Handle Unix timestamp
            if isinstance(created_time, (int, float)):
                from datetime import datetime
                created_date = datetime.fromtimestamp(created_time)
                days_old = (datetime.now() - created_date).days
                is_recent = days_old <= 7  # Posts from last week
                return (days_old, is_recent)
            
            # Handle string date
            from datetime import datetime
            created_date = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
            days_old = (datetime.now(created_date.tzinfo) - created_date).days
            is_recent = days_old <= 7
            
            return (days_old, is_recent)
        except Exception as e:
            print(f"❌ Error parsing date '{created_time}': {e}")
            # Return reasonable defaults if date parsing fails
            return (3, True)  # 3 days old, considered recent
    
    def _calculate_trend_score(self, score: int, days_old: int, comments_count: int) -> float:
        """Calculate trend score for a post"""
        trend_score = 0.0
        
        # Score bonus
        if score > 100:
            trend_score += 30
        elif score > 50:
            trend_score += 20
        elif score > 20:
            trend_score += 10
        
        # Recency bonus
        if days_old <= 1:
            trend_score += 25
        elif days_old <= 3:
            trend_score += 15
        elif days_old <= 7:
            trend_score += 5
        
        # Engagement bonus (comments)
        if comments_count > 50:
            trend_score += 20
        elif comments_count > 20:
            trend_score += 10
        elif comments_count > 5:
            trend_score += 5
        
        return round(min(trend_score, 100), 2)
    
    def _calculate_engagement_metrics(self, results: List[Dict]) -> Dict:
        """Calculate HackerNews engagement metrics"""
        if not results:
            return {"post_count": 0}
        
        post_count = len(results)
        total_score = sum(post.get('score', 0) for post in results)
        total_comments = sum(post.get('comments_count', 0) for post in results)
        recent_posts = len([post for post in results if post.get('is_recent', False)])
        
        metrics = {
            "post_count": post_count,
            "recent_posts": recent_posts,
            "avg_score": round(total_score / post_count, 2) if post_count > 0 else 0,
            "avg_comments": round(total_comments / post_count, 2) if post_count > 0 else 0,
            "total_score": total_score,
            "total_comments": total_comments
        }
        
        # Top authors
        authors = [post.get('author', '') for post in results if post.get('author')]
        if authors:
            from collections import Counter
            author_counts = Counter(authors)
            metrics["top_authors"] = dict(author_counts.most_common(3))
        
        return metrics

    def _translate_keyword_with_claude(self, keyword: str) -> str:
        """Translate Japanese keyword to English using Claude API"""
        print(f"🔍 Claude client available: {self.claude_client is not None}")
        if not self.claude_client:
            print("⚠️ Claude client not available, using fallback translation")
            return self._translate_keyword_to_english_fallback(keyword)
        
        try:
            prompt = f"""
あなたはAI研究分野の専門家です。以下の日本語のキーワードを、arXivで検索するのに適した英語のキーワードに翻訳してください。

日本語キーワード: {keyword}

以下の点に注意してください：
1. AI研究分野で一般的に使用される英語の専門用語を使用
2. arXivで検索する際に効果的なキーワードを選択
3. 複数の関連キーワードがある場合は、最も適切なものを1つ選択
4. 回答は英語のキーワードのみで、説明は不要

英語キーワード:"""

            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=50,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            english_keyword = response.content[0].text.strip()
            print(f"🤖 Claude translated '{keyword}' -> '{english_keyword}'")
            return english_keyword
            
        except Exception as e:
            print(f"❌ Claude translation error: {e}, using fallback")
            return self._translate_keyword_to_english_fallback(keyword)
    
    def _translate_keyword_to_english_fallback(self, keyword: str) -> str:
        """Fallback translation method using hardcoded dictionary"""
        # Common Japanese to English translations for AI research
        translations = {
            "生成AI": "generative AI",
            "人工知能": "artificial intelligence",
            "機械学習": "machine learning",
            "深層学習": "deep learning",
            "自然言語処理": "natural language processing",
            "コンピュータビジョン": "computer vision",
            "強化学習": "reinforcement learning",
            "ニューラルネットワーク": "neural networks",
            "大規模言語モデル": "large language models",
            "LLM": "large language models",
            "GPT": "GPT",
            "ChatGPT": "ChatGPT",
            "画像生成": "image generation",
            "音声認識": "speech recognition",
            "音声合成": "speech synthesis",
            "推薦システム": "recommendation systems",
            "異常検知": "anomaly detection",
            "時系列予測": "time series prediction",
            "クラスタリング": "clustering",
            "分類": "classification"
        }
        
        # Direct translation
        if keyword in translations:
            return translations[keyword]
        
        # Try partial matches
        for jp, en in translations.items():
            if jp in keyword or keyword in jp:
                return en
        
        # If no translation found, try to use the keyword as-is
        # Many Japanese researchers use English terms in their papers
        return keyword
    
    def _get_broader_keywords_with_claude(self, keyword: str) -> List[str]:
        """Get broader search terms for fallback searches using Claude API"""
        if not self.claude_client:
            print("⚠️ Claude client not available, using fallback broader keywords")
            return self._get_broader_keywords_fallback(keyword)
        
        try:
            prompt = f"""
あなたはAI研究分野の専門家です。以下の英語のキーワードでHackerNews検索を行ったが結果が見つからなかった場合、より一般的で広範囲な検索キーワードを3つ提案してください。

元のキーワード: {keyword}

以下の点に注意してください：
1. より一般的で広範囲なAI関連のキーワードを提案
2. 元のキーワードより具体的でない、より包括的なキーワードを選択
3. HackerNewsで検索する際に効果的なキーワードを選択
4. 回答は英語のキーワードのみで、カンマ区切りで3つ提案

提案するキーワード:"""

            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=100,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            broader_keywords_text = response.content[0].text.strip()
            # Parse comma-separated keywords
            broader_keywords = [kw.strip() for kw in broader_keywords_text.split(',') if kw.strip()]
            
            print(f"🤖 Claude suggested broader keywords: '{keyword}' -> {broader_keywords}")
            return broader_keywords[:3]  # Limit to 3 keywords
            
        except Exception as e:
            print(f"❌ Claude broader keywords error: {e}, using fallback")
            return keyword


class PlatformHandlerFactory:
    """Factory for creating platform handlers"""
    
    @staticmethod
    def create_handler(platform: str, claude_client=None) -> BasePlatformHandler:
        """Create appropriate handler for platform"""
        handlers = {
            "youtube": YouTubeHandler,
            "github": GitHubHandler,
            "web": WebHandler,
            "arxiv": lambda: ArxivHandler(claude_client),
            "hackernews": lambda: HackerNewsHandler(claude_client)
        }
        
        handler_class = handlers.get(platform)
        if handler_class:
            if platform == "arxiv":
                return handler_class()
            else:
                return handler_class()
        else:
            raise ValueError(f"No handler available for platform: {platform}")