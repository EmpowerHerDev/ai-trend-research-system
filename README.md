# AI Trend Research System

## Overview
An automated system that uses MCP (Model Context Protocol) to collect AI trend information from multiple platforms and generate comprehensive research reports.

## Features
- **Keyword Management**: Dynamic keyword system with master/active lists
- **Multi-Platform Research**: Twitter, YouTube, GitHub, Reddit, LinkedIn, arXiv, etc.
- **Automated Execution**: Daily research via GitHub Actions
- **Report Generation**: Structured JSON reports with insights
- **Keyword Discovery**: Automatic detection of new trending keywords

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
└── .github/workflows/   # GitHub Actions automation
```

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Set up GitHub secrets:
   - `ANTHROPIC_API_KEY`: Your Claude API key
3. Configure MCP connections for each platform

## Usage
- **Manual execution**: `python ai_trend_researcher.py`
- **Automated**: Runs daily at 9:00 AM JST via GitHub Actions

## Keyword Management
- Keywords are scored based on engagement and relevance
- New keywords are automatically discovered and added to master.json
- Active keywords are selected from highest-scoring entries
- Execution history tracks research patterns and success rates