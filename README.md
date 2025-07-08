# AI Trend Research System

## Overview
An automated system that uses MCP (Model Context Protocol) to collect AI trend information from multiple platforms and generate comprehensive research reports.

## Features
- **Keyword Management**: Dynamic keyword system with master/active lists
- **Multi-Platform Research**: Twitter, YouTube, GitHub, Reddit, LinkedIn, arXiv, etc.
- **Automated Execution**: Daily research via GitHub Actions
- **Report Generation**: Structured JSON reports with insights
- **Keyword Discovery**: Automatic detection of new trending keywords
- **Multi-Platform Storage**: Reports saved to JSON, Notion, and Supabase

## File Structure
```
ai-trend-research-system/
├── keywords/
│   ├── master.json      # All keywords with metadata
│   ├── active.json      # Current research keywords
│   └── history.json     # Execution history
├── reports/             # Generated research reports
├── ai_trend_researcher.py  # Main research script
├── keyword_manager.py   # Keyword management utilities
├── supabase_schema.sql  # Supabase database schema
└── .github/workflows/   # GitHub Actions automation
```

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Install MCP servers:
   - **Web Search**: `npm install -g one-search-mcp`
   - **Notion**: `npm install -g @ramidecodes/mcp-server-notion`
   - **Supabase**: `npm install -g @supabase/mcp-server-supabase`
   - Other MCP servers can be configured as needed
3. Set up environment variables:
   - `ANTHROPIC_API_KEY`: Your Claude API key
   - `YOUTUBE_API_KEY`: YouTube Data API key
   - `GITHUB_PERSONAL_ACCESS_TOKEN`: GitHub personal access token
   - `NOTION_API_KEY`: Notion API key
   - `NOTION_PARENT_PAGE_ID`: Notion parent page ID
   - `SUPABASE_ACCESS_TOKEN`: Supabase access token
4. Configure MCP connections for each platform
5. Set up Supabase database:
   - Create a new Supabase project
   - Run the SQL commands in `supabase_schema.sql` to create the required tables
   - Generate an access token in your Supabase dashboard

## Usage
- **Manual execution**: `python ai_trend_researcher.py`
- **Automated**: Runs daily at 9:00 AM JST via GitHub Actions

## Report Storage
Reports are automatically saved to:
- **JSON files**: Local storage in `reports/` directory
- **Notion**: Structured pages in your Notion workspace
- **Supabase**: Database table `ai_trend_reports` for programmatic access

## Keyword Management
- Keywords are scored based on engagement and relevance
- New keywords are automatically discovered and added to master.json
- Active keywords are selected from highest-scoring entries
- Execution history tracks research patterns and success rates