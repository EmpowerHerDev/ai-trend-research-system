import json
import os
from datetime import datetime
from typing import Dict, List, Any
from mcp_client_manager import RemoteMCPClient


class JSONReportGenerator:
    """Generates JSON reports from research data"""
    
    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = reports_dir
    
    def generate_report(self, research_data: List[Dict], new_keywords: List[str], 
                       summary: Dict[str, Any], recommendations: List[str]) -> str:
        """Generate JSON research report"""
        today = datetime.now().strftime("%Y-%m-%d")
        report = {
            "date": today,
            "summary": summary,
            "detailed_results": research_data,
            "new_keywords": new_keywords,
            "recommendations": recommendations
        }
        
        report_file = os.path.join(self.reports_dir, f"ai_trends_{today}.json")
        os.makedirs(self.reports_dir, exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report_file


class NotionReportGenerator:
    """Generates reports in Notion using MCP server"""
    
    def __init__(self, notion_client: RemoteMCPClient, parent_page_id: str):
        self.notion_client = notion_client
        self.parent_page_id = parent_page_id
    
    async def create_notion_report(self, report: Dict) -> Any:
        """Create organized report in Notion using MCP server"""
        if not self.notion_client or not self.parent_page_id:
            print("Notion MCP server or parent page ID not available, skipping Notion report")
            return None
        
        try:
            today = report["date"]
            page_title = f"AI Trend Research Report - {today}"
            
            response = await self.notion_client.call_tool(
                "create-page",
                {
                    "parent_type": "page_id",
                    "parent_id": self.parent_page_id,
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
            return None
    
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
        
        # Add recommendations section
        blocks.append({
            "object": "block",
            "type": "heading_2", 
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📋 Recommendations"}}]
            }
        })
        
        for rec in report["recommendations"]:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": rec}}]
                }
            })
        
        # Add detailed results section
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🔬 Detailed Research Results"}}]
            }
        })
        
        # Group results by platform
        platform_results = self._group_results_by_platform(report["detailed_results"])
        
        for platform, results in platform_results.items():
            # Platform heading
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": platform.upper()}}]
                }
            })
            
            if results:
                for i, result in enumerate(results[:5], 1):  # Limit to top 5 results
                    title = result.get('title', result.get('name', 'No title'))
                    url = result.get('url', result.get('link', ''))
                    snippet = result.get('snippet', result.get('description', ''))[:200]
                    
                    # Result item
                    blocks.append({
                        "object": "block",
                        "type": "heading_4",
                        "heading_4": {
                            "rich_text": [{"type": "text", "text": {"content": f"{i}. {title}"}}]
                        }
                    })
                    
                    if url:
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": f"🔗 {url}"}}]
                            }
                        })
                    
                    if snippet:
                        blocks.append({
                            "object": "block",
                            "type": "paragraph", 
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": f"📝 {snippet}..."}}]
                            }
                        })
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": "- No results found"}}]
                    }
                })
        
        return blocks
    
    def _group_results_by_platform(self, detailed_results: List[Dict]) -> Dict[str, List[Dict]]:
        """Group results by platform"""
        platform_results = {}
        for data in detailed_results:
            platform = data["platform"]
            if platform not in platform_results:
                platform_results[platform] = []
            platform_results[platform].extend(data["results"])
        return platform_results


class ReportManager:
    """Manages both JSON and Notion report generation"""
    
    def __init__(self, reports_dir: str = "reports", notion_client: RemoteMCPClient = None, 
                 notion_parent_id: str = None):
        self.json_generator = JSONReportGenerator(reports_dir)
        self.notion_generator = NotionReportGenerator(notion_client, notion_parent_id) if notion_client else None
    
    async def generate_all_reports(self, research_data: List[Dict], new_keywords: List[str],
                                 summary: Dict[str, Any], recommendations: List[str]) -> str:
        """Generate both JSON and Notion reports"""
        # Generate JSON report
        report_file = self.json_generator.generate_report(
            research_data, new_keywords, summary, recommendations
        )
        
        # Generate Notion report if available
        if self.notion_generator:
            report_data = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "summary": summary,
                "detailed_results": research_data,
                "new_keywords": new_keywords,
                "recommendations": recommendations
            }
            await self.notion_generator.create_notion_report(report_data)
        
        return report_file