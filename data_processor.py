import json
import re
from typing import Dict, List, Any
from anthropic import Anthropic


class KeywordExtractor:
    """Extracts new keywords from research data using Claude AI"""
    
    def __init__(self, claude_client: Anthropic):
        self.claude_client = claude_client
    
    async def extract_keywords(self, research_data: List[Dict]) -> List[str]:
        """Extract new keywords using Claude AI"""
        if not research_data or not self.claude_client:
            print("No research data or Claude client available for keyword extraction")
            return []
        
        content_summary = self._prepare_content_for_analysis(research_data)
        if not content_summary:
            print("No content found in research data for keyword extraction")
            return []
        
        try:
            prompt = self._create_extraction_prompt(content_summary)
            response = await self._call_claude(prompt)
            keywords = self._parse_keywords_from_response(response)
            print(f"Claude extracted {len(keywords)} keywords: {keywords}")
            return keywords
            
        except Exception as e:
            print(f"Claude keyword extraction error: {e}")
            return []
    
    def _prepare_content_for_analysis(self, research_data: List[Dict]) -> List[Dict]:
        """Prepare content summary for Claude analysis"""
        content_summary = []
        for data in research_data:
            if data.get('results'):
                for result in data['results'][:3]:  # Limit to first 3 results per platform
                    content_summary.append({
                        'platform': data['platform'],
                        'keyword': data['keyword'],
                        'title': result.get('title', ''),
                        'description': result.get('description', result.get('snippet', ''))[:200]
                    })
        return content_summary
    
    def _create_extraction_prompt(self, content_summary: List[Dict]) -> str:
        """Create prompt for Claude keyword extraction"""
        return f"""Analyze this AI trend research data and extract 5-10 new trending keywords related to AI, machine learning, or technology.
        
Data: {json.dumps(content_summary, indent=2, ensure_ascii=False)}
        
Instructions:
1. Focus on AI tools, frameworks, companies, techniques, or emerging technologies
2. Return only a JSON array of keywords, like: ["keyword1", "keyword2", "keyword3"]
3. Prioritize keywords that appear frequently or have high engagement
4. Include both English and Japanese keywords if relevant
5. If no relevant keywords are found, return an empty array: []
"""
    
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
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                keywords = json.loads(json_match.group())
                return [k.strip() for k in keywords if isinstance(k, str) and k.strip()]
        except Exception as e:
            print(f"Error parsing keywords: {e}")
        
        # Fallback: extract words that look like keywords
        words = response.replace('"', '').replace('[', '').replace(']', '').split(',')
        return [w.strip() for w in words if w.strip() and len(w.strip()) > 2][:10]


class DataAnalyzer:
    """Analyzes research data and calculates metrics"""
    
    @staticmethod
    def score_keywords(keywords: List[str], research_data: List[Dict]) -> Dict[str, int]:
        """Score new keywords based on research data"""
        scores = {}
        for keyword in keywords:
            base_score = 50
            mention_count = sum(1 for data in research_data if keyword.lower() in str(data).lower())
            scores[keyword] = min(100, base_score + mention_count * 5)
        
        return scores
    
    @staticmethod
    def generate_recommendations(research_data: List[Dict], new_keywords: List[str]) -> List[str]:
        """Generate recommendations based on research"""
        recommendations = []
        
        if new_keywords:
            recommendations.append(f"Consider adding {len(new_keywords)} new keywords to monitoring")
        
        high_engagement_platforms = [
            d["platform"] for d in research_data 
            if d.get("sentiment_score", 0) > 0.7
        ]
        if high_engagement_platforms:
            recommendations.append(
                f"High engagement detected on: {', '.join(set(high_engagement_platforms))}"
            )
        
        return recommendations
    
    @staticmethod
    def calculate_summary_stats(research_data: List[Dict], new_keywords: List[str]) -> Dict[str, Any]:
        """Calculate summary statistics from research data"""
        return {
            "platforms_searched": len(set(d["platform"] for d in research_data)),
            "keywords_used": list(set(d["keyword"] for d in research_data)),
            "new_keywords_found": len(new_keywords),
            "total_results": sum(len(d["results"]) for d in research_data)
        }