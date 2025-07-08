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
            today = report.get("date", datetime.now().strftime("%Y-%m-%d"))
            page_title = f"AI Trend Research Report - {today}"
            
            # Try simplified blocks first to avoid validation issues
            print("🔍 Creating simplified Notion blocks...")
            blocks = self._create_simple_notion_blocks(report)
            
            # Debug: Print block count and structure
            print(f"🔍 Created {len(blocks)} simplified blocks for Notion")
            self._debug_print_blocks(blocks, "Simplified blocks")
            
            # Ensure we have at least some content
            if not blocks:
                print("Warning: No valid blocks created, skipping Notion report")
                return None
            
            # Validate the blocks structure before sending
            if not self._validate_blocks_structure(blocks):
                print("Warning: Invalid blocks structure, trying detailed blocks...")
                # Fallback to detailed blocks if simplified fails validation
                blocks = self._create_notion_blocks(report)
                if not self._validate_blocks_structure(blocks):
                    print("Warning: Detailed blocks also failed validation, skipping Notion report")
                    return None
            
            # Final validation: Ensure each block has the exact structure Notion expects
            validated_blocks = self._final_validate_blocks(blocks)
            if not validated_blocks:
                print("Warning: Final validation failed, skipping Notion report")
                return None
            
            print(f"✅ Final validation passed: {len(validated_blocks)} blocks ready for Notion")
            self._debug_print_blocks(validated_blocks, "Validated blocks")
            
            # Check if we have block 17 (index 16) and print its details
            if len(validated_blocks) > 16:
                print(f"🔍 Block 17 (index 16) details:")
                block_17 = validated_blocks[16]
                print(f"  Type: {block_17.get('type')}")
                print(f"  Content: {json.dumps(block_17, indent=2, ensure_ascii=False)}")
            
            # Debug: Print the exact JSON being sent
            children_json = json.dumps(validated_blocks, ensure_ascii=False)
            print(f"🔍 JSON being sent to Notion (first 500 chars): {children_json[:500]}...")
            
            # Try a different approach: limit the number of blocks to avoid the issue
            # Notion might have a limit or issue with too many blocks
            if len(validated_blocks) > 20:
                print(f"⚠️ Too many blocks ({len(validated_blocks)}), limiting to first 20")
                limited_blocks = validated_blocks[:20]
            else:
                limited_blocks = validated_blocks
            
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
                    "children": json.dumps(limited_blocks)
                }
            )
            
            print(f"✓ Notion report created: {page_title}")
            return response
            
        except Exception as e:
            print(f"✗ Error creating Notion report: {e}")
            return None
    
    def _validate_blocks_structure(self, blocks: List[Dict]) -> bool:
        """Validate that all blocks have the correct structure for Notion API"""
        if not isinstance(blocks, list):
            print("Error: blocks is not a list")
            return False
        
        for i, block in enumerate(blocks):
            if not isinstance(block, dict):
                print(f"Error: Block {i} is not a dictionary")
                return False
            
            # Check required fields
            if "object" not in block or block["object"] != "block":
                print(f"Error: Block {i} missing or invalid 'object' field")
                return False
            
            if "type" not in block:
                print(f"Error: Block {i} missing 'type' field")
                return False
            
            block_type = block["type"]
            if block_type not in block:
                print(f"Error: Block {i} missing content for type '{block_type}'")
                return False
            
            # Validate rich_text structure
            if "rich_text" in block[block_type]:
                rich_text = block[block_type]["rich_text"]
                if not isinstance(rich_text, list):
                    print(f"Error: Block {i} rich_text is not a list")
                    return False
                
                if len(rich_text) == 0:
                    print(f"Error: Block {i} has empty rich_text")
                    return False
                
                for j, text_item in enumerate(rich_text):
                    if not isinstance(text_item, dict):
                        print(f"Error: Block {i} text item {j} is not a dictionary")
                        return False
                    
                    if "type" not in text_item or text_item["type"] != "text":
                        print(f"Error: Block {i} text item {j} has invalid type")
                        return False
                    
                    if "text" not in text_item:
                        print(f"Error: Block {i} text item {j} missing 'text' field")
                        return False
                    
                    content = text_item["text"].get("content", "")
                    if not content or not content.strip():
                        print(f"Error: Block {i} text item {j} has empty content")
                        return False
        
        return True
    
    def _create_notion_blocks(self, report: Dict) -> List[Dict]:
        """Create Notion blocks from report data"""
        # Validate input report
        if not isinstance(report, dict):
            print("Error: report is not a dictionary")
            return []
        
        blocks = []
        
        try:
            # Add summary section
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📊 Summary"}}]
                }
            })
            
            summary = report.get("summary", {})
            if not isinstance(summary, dict):
                summary = {}
                
            summary_text = f"• Platforms Searched: {summary.get('platforms_searched', 'N/A')}\n"
            summary_text += f"• Keywords Used: {', '.join(summary.get('keywords_used', []))}\n"
            summary_text += f"• New Keywords Found: {summary.get('new_keywords_found', 0)}\n"
            summary_text += f"• Total Results: {summary.get('total_results', 0)}"
            
            # Ensure summary text is not empty
            if not summary_text.strip():
                summary_text = "No summary data available"
            
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
            
            new_keywords = report.get("new_keywords", [])
            if not isinstance(new_keywords, list):
                new_keywords = []
                
            if new_keywords:
                for keyword in new_keywords:
                    if keyword and isinstance(keyword, str) and keyword.strip():  # Ensure keyword is not empty
                        blocks.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [{"type": "text", "text": {"content": keyword.strip()}}]
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
            
            recommendations = report.get("recommendations", [])
            if not isinstance(recommendations, list):
                recommendations = []
                
            if recommendations:
                for rec in recommendations:
                    if rec and isinstance(rec, str) and rec.strip():  # Ensure recommendation is not empty
                        blocks.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [{"type": "text", "text": {"content": rec.strip()}}]
                            }
                        })
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": "No recommendations available"}}]
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
            detailed_results = report.get("detailed_results", [])
            if not isinstance(detailed_results, list):
                detailed_results = []
                
            platform_results = self._group_results_by_platform(detailed_results)
            
            if platform_results:
                for platform, results in platform_results.items():
                    # Ensure platform name is valid
                    if not platform or not isinstance(platform, str):
                        platform = "Unknown"
                    
                    # Platform heading
                    blocks.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"type": "text", "text": {"content": platform.upper()}}]
                        }
                    })
                    
                    if results and isinstance(results, list):
                        for i, result in enumerate(results[:5], 1):  # Limit to top 5 results
                            if not isinstance(result, dict):
                                continue
                                
                            title = result.get('title', result.get('name', 'No title'))
                            url = result.get('url', result.get('link', ''))
                            snippet = result.get('snippet', result.get('description', ''))
                            
                            # Ensure title is not empty and is a string
                            if not title or not isinstance(title, str) or not title.strip():
                                title = "Untitled"
                            
                            # Result item
                            blocks.append({
                                "object": "block",
                                "type": "heading_4",
                                "heading_4": {
                                    "rich_text": [{"type": "text", "text": {"content": f"{i}. {title}"}}]
                                }
                            })
                            
                            if url and isinstance(url, str) and url.strip():
                                blocks.append({
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [{"type": "text", "text": {"content": f"🔗 {url}"}}]
                                    }
                                })
                            
                            if snippet and isinstance(snippet, str) and snippet.strip():
                                # Truncate snippet to avoid too long content
                                snippet_text = snippet[:200] + "..." if len(snippet) > 200 else snippet
                                blocks.append({
                                    "object": "block",
                                    "type": "paragraph", 
                                    "paragraph": {
                                        "rich_text": [{"type": "text", "text": {"content": f"📝 {snippet_text}"}}]
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
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": "No detailed results available"}}]
                    }
                })
            
        except Exception as e:
            print(f"Error creating Notion blocks: {e}")
            # Return minimal valid blocks if there's an error
            return [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": "Error occurred while generating report content."}}]
                    }
                }
            ]
        
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
    
    def _final_validate_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """Final validation to ensure blocks have exact Notion API structure"""
        validated_blocks = []
        
        for i, block in enumerate(blocks):
            try:
                # Ensure block is a dictionary
                if not isinstance(block, dict):
                    print(f"❌ Block {i}: Not a dictionary, skipping")
                    continue
                
                # Ensure required fields exist
                if "object" not in block or block["object"] != "block":
                    print(f"❌ Block {i}: Missing or invalid 'object' field")
                    continue
                
                if "type" not in block:
                    print(f"❌ Block {i}: Missing 'type' field")
                    continue
                
                block_type = block["type"]
                
                # Ensure the block type field exists
                if block_type not in block:
                    print(f"❌ Block {i}: Missing content for type '{block_type}'")
                    continue
                
                # Validate the specific block type structure
                if not self._validate_block_type_structure(block, block_type, i):
                    continue
                
                # Create a clean, validated block
                validated_block = {
                    "object": "block",
                    "type": block_type,
                    block_type: block[block_type]
                }
                
                validated_blocks.append(validated_block)
                print(f"✅ Block {i}: Validated {block_type}")
                
            except Exception as e:
                print(f"❌ Block {i}: Error during validation: {e}")
                continue
        
        return validated_blocks
    
    def _validate_block_type_structure(self, block: Dict, block_type: str, block_index: int) -> bool:
        """Validate the structure of a specific block type"""
        try:
            block_content = block[block_type]
            
            # Validate rich_text structure for text-based blocks
            if "rich_text" in block_content:
                rich_text = block_content["rich_text"]
                
                if not isinstance(rich_text, list):
                    print(f"❌ Block {block_index}: rich_text is not a list")
                    return False
                
                if len(rich_text) == 0:
                    print(f"❌ Block {block_index}: rich_text is empty")
                    return False
                
                for j, text_item in enumerate(rich_text):
                    if not isinstance(text_item, dict):
                        print(f"❌ Block {block_index}: text item {j} is not a dictionary")
                        return False
                    
                    if "type" not in text_item or text_item["type"] != "text":
                        print(f"❌ Block {block_index}: text item {j} has invalid type")
                        return False
                    
                    if "text" not in text_item:
                        print(f"❌ Block {block_index}: text item {j} missing 'text' field")
                        return False
                    
                    text_content = text_item["text"]
                    if not isinstance(text_content, dict):
                        print(f"❌ Block {block_index}: text item {j} 'text' is not a dictionary")
                        return False
                    
                    if "content" not in text_content:
                        print(f"❌ Block {block_index}: text item {j} missing 'content' field")
                        return False
                    
                    content = text_content["content"]
                    if not isinstance(content, str) or not content.strip():
                        print(f"❌ Block {block_index}: text item {j} has empty content")
                        return False
                    
                    # Ensure content is not too long (Notion has limits)
                    if len(content) > 2000:
                        print(f"⚠️ Block {block_index}: text item {j} content is too long, truncating")
                        text_content["content"] = content[:2000] + "..."
            
            return True
            
        except Exception as e:
            print(f"❌ Block {block_index}: Error validating {block_type} structure: {e}")
            return False

    def _debug_print_blocks(self, blocks: List[Dict], title: str = "Blocks"):
        """Debug function to print block information"""
        print(f"\n🔍 {title} ({len(blocks)} blocks):")
        for i, block in enumerate(blocks):
            try:
                block_type = block.get("type", "unknown")
                print(f"  Block {i}: {block_type}")
                
                if block_type in block:
                    content = block[block_type]
                    if "rich_text" in content:
                        rich_text = content["rich_text"]
                        if isinstance(rich_text, list) and len(rich_text) > 0:
                            first_text = rich_text[0]
                            if isinstance(first_text, dict) and "text" in first_text:
                                text_content = first_text["text"].get("content", "")
                                preview = text_content[:50] + "..." if len(text_content) > 50 else text_content
                                print(f"    Content: {preview}")
                            else:
                                print(f"    Content: Invalid rich_text structure")
                        else:
                            print(f"    Content: Empty or invalid rich_text")
                    else:
                        print(f"    Content: No rich_text field")
                else:
                    print(f"    Content: Missing {block_type} field")
                    
            except Exception as e:
                print(f"    Error analyzing block {i}: {e}")
        print()

    def _create_simple_notion_blocks(self, report: Dict) -> List[Dict]:
        """Create simplified Notion blocks to avoid validation issues"""
        blocks = []
        
        try:
            # Add title
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": f"AI Trend Research Report - {report.get('date', 'Today')}"}}]
                }
            })
            
            # Add summary
            summary = report.get("summary", {})
            if isinstance(summary, dict):
                summary_text = f"Platforms: {summary.get('platforms_searched', 'N/A')} | Keywords: {len(summary.get('keywords_used', []))} | New Keywords: {summary.get('new_keywords_found', 0)} | Total Results: {summary.get('total_results', 0)}"
            else:
                summary_text = "Summary data not available"
            
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": summary_text}}]
                }
            })
            
            # Add new keywords
            new_keywords = report.get("new_keywords", [])
            if isinstance(new_keywords, list) and new_keywords:
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "New Keywords"}}]
                    }
                })
                
                # Add keywords as a single paragraph to reduce block count
                keywords_text = ", ".join([kw for kw in new_keywords if isinstance(kw, str) and kw.strip()])
                if keywords_text:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": keywords_text}}]
                        }
                    })
            
            # Add recommendations
            recommendations = report.get("recommendations", [])
            if isinstance(recommendations, list) and recommendations:
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "Recommendations"}}]
                    }
                })
                
                # Add recommendations as a single paragraph
                rec_text = " | ".join([rec for rec in recommendations if isinstance(rec, str) and rec.strip()])
                if rec_text:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": rec_text}}]
                        }
                    })
            
            # Add platform results (simplified)
            detailed_results = report.get("detailed_results", [])
            if isinstance(detailed_results, list) and detailed_results:
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "Research Results"}}]
                    }
                })
                
                # Group by platform and add summary
                platform_results = self._group_results_by_platform(detailed_results)
                for platform, results in platform_results.items():
                    if isinstance(results, list) and results:
                        platform_text = f"{platform.upper()}: {len(results)} results"
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": platform_text}}]
                            }
                        })
            
        except Exception as e:
            print(f"Error creating simple Notion blocks: {e}")
            # Return minimal valid blocks if there's an error
            return [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": "Error occurred while generating report content."}}]
                    }
                }
            ]
        
        return blocks


class SupabaseReportGenerator:
    """Generates reports in Supabase using MCP server"""
    
    def __init__(self, supabase_client: RemoteMCPClient):
        self.supabase_client = supabase_client
    
    async def create_supabase_report(self, report: Dict) -> Any:
        """Create report in Supabase using MCP server"""
        if not self.supabase_client:
            print("Supabase MCP server not available, skipping Supabase report")
            return None
        
        try:
            today = report.get("date", datetime.now().strftime("%Y-%m-%d"))
            
            # Prepare the report data for Supabase
            report_data = {
                "date": today,
                "summary": report.get("summary", {}),
                "detailed_results": report.get("detailed_results", []),
                "new_keywords": report.get("new_keywords", []),
                "recommendations": report.get("recommendations", []),
                "created_at": datetime.now().isoformat()
            }
            
            print(f"🔍 Inserting report into Supabase for date: {today}")
            
            project_id = "vfzumtgiwrwluphbagrg"

            sql = """
            INSERT INTO ai_trend_reports (date, summary, detailed_results, new_keywords, recommendations, created_at)
            VALUES ('{date}', '{summary}', '{detailed_results}', '{new_keywords}', '{recommendations}', '{created_at}')
            RETURNING id
            """

            params = {
                "date": report_data["date"],
                "summary": json.dumps(report_data["summary"], ensure_ascii=False).replace("'", "''"),
                "detailed_results": json.dumps(report_data["detailed_results"], ensure_ascii=False).replace("'", "''"),
                "new_keywords": json.dumps(report_data["new_keywords"], ensure_ascii=False).replace("'", "''"),
                "recommendations": json.dumps(report_data["recommendations"], ensure_ascii=False).replace("'", "''"),
                "created_at": report_data["created_at"]
            }

            query = sql.format(**params)

            response = await self.supabase_client.call_tool(
                "execute_sql",
                {
                    "project_id": project_id,
                    "query": query
                }
            )
            
            print(f"✓ Supabase report created for date: {today}")
            print(f"Supabase insert response: {response}")
            return response
            
        except Exception as e:
            print(f"✗ Error creating Supabase report: {e}")
            return None


class ReportManager:
    """Manages both JSON and Notion report generation"""
    
    def __init__(self, reports_dir: str = "reports", notion_client: RemoteMCPClient = None, 
                 notion_parent_id: str = None, supabase_client: RemoteMCPClient = None):
        self.json_generator = JSONReportGenerator(reports_dir)
        self.notion_generator = NotionReportGenerator(notion_client, notion_parent_id) if notion_client else None
        self.supabase_generator = SupabaseReportGenerator(supabase_client) if supabase_client else None
    
    async def generate_all_reports(self, research_data: List[Dict], new_keywords: List[str],
                                 summary: Dict[str, Any], recommendations: List[str]) -> str:
        """Generate JSON, Notion, and Supabase reports"""
        # Generate JSON report
        report_file = self.json_generator.generate_report(
            research_data, new_keywords, summary, recommendations
        )
        
        # Prepare report data for other platforms
        report_data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "summary": summary,
            "detailed_results": research_data,
            "new_keywords": new_keywords,
            "recommendations": recommendations
        }
        
        # Generate Notion report if available
        if self.notion_generator:
            await self.notion_generator.create_notion_report(report_data)
        
        # Generate Supabase report if available
        if self.supabase_generator:
            await self.supabase_generator.create_supabase_report(report_data)
        
        return report_file