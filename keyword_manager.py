import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class KeywordManager:
    def __init__(self, keywords_dir: str = "keywords"):
        self.keywords_dir = keywords_dir
        self.master_file = os.path.join(keywords_dir, "master.json")
        self.active_file = os.path.join(keywords_dir, "active.json")
        self.history_file = os.path.join(keywords_dir, "history.json")
    
    def load_master_keywords(self) -> Dict:
        """Load master keywords from JSON file"""
        try:
            with open(self.master_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def load_active_keywords(self) -> List[str]:
        """Load active keywords from JSON file"""
        try:
            with open(self.active_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def load_history(self) -> Dict:
        """Load execution history from JSON file"""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_master_keywords(self, keywords: Dict):
        """Save master keywords to JSON file"""
        with open(self.master_file, 'w', encoding='utf-8') as f:
            json.dump(keywords, f, ensure_ascii=False, indent=2)
    
    def save_active_keywords(self, keywords: List[str]):
        """Save active keywords to JSON file"""
        with open(self.active_file, 'w', encoding='utf-8') as f:
            json.dump(keywords, f, ensure_ascii=False, indent=2)
    
    def save_history(self, history: Dict):
        """Save execution history to JSON file"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def add_new_keyword(self, keyword: str, score: int = 50, source: str = "discovered", discovered_from: Optional[str] = None):
        """Add new keyword to master list"""
        master = self.load_master_keywords()
        
        if keyword not in master:
            master[keyword] = {
                "score": score,
                "last_used": None,
                "source": source,
                "created_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            if discovered_from:
                master[keyword]["discovered_from"] = discovered_from
            
            self.save_master_keywords(master)
            return True
        return False
    
    def update_keyword_score(self, keyword: str, new_score: int):
        """Update keyword score"""
        master = self.load_master_keywords()
        if keyword in master:
            master[keyword]["score"] = new_score
            self.save_master_keywords(master)
            return True
        return False
    
    def mark_keywords_used(self, keywords: List[str]):
        """Mark keywords as used today"""
        master = self.load_master_keywords()
        today = datetime.now().strftime("%Y-%m-%d")
        
        for keyword in keywords:
            if keyword in master:
                master[keyword]["last_used"] = today
        
        self.save_master_keywords(master)
    
    def record_execution(self, keywords: List[str], status: str = "completed", new_keywords_found: int = 0):
        """Record execution in history"""
        history = self.load_history()
        today = datetime.now().strftime("%Y-%m-%d")
        
        history[today] = {
            "keywords": keywords,
            "execution_time": datetime.now().strftime("%H:%M:%S"),
            "status": status,
            "new_keywords_found": new_keywords_found
        }
        
        self.save_history(history)
    
    def get_top_keywords(self, limit: int = 10) -> List[str]:
        """Get top keywords by score"""
        master = self.load_master_keywords()
        sorted_keywords = sorted(master.items(), key=lambda x: x[1]["score"], reverse=True)
        return [keyword for keyword, _ in sorted_keywords[:limit]]
    
    def refresh_active_keywords(self, limit: int = 5):
        """Refresh active keywords with top scoring ones"""
        top_keywords = self.get_top_keywords(limit)
        self.save_active_keywords(top_keywords)
        return top_keywords