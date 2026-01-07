"""Cache manager for AI-generated content"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class CacheManager:
    """Manages cache for AI-generated content to avoid redundant API calls"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            cache_dir = Path.home() / ".repo-analyzer" / "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_days = 7  # Cache expires after 7 days
    
    def get_cache_key(self, content_type: str, data: Dict[str, Any]) -> str:
        """Generate cache key from content type and data"""
        # Create a hash from the data
        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()[:16]
        return f"{content_type}_{data_hash}"
    
    def get(self, cache_key: str) -> Optional[str]:
        """Get cached content if available and not expired"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check if cache is expired
            cached_at = datetime.fromisoformat(cache_data.get("cached_at", ""))
            if datetime.now() - cached_at > timedelta(days=self.cache_ttl_days):
                # Cache expired, delete file
                cache_file.unlink()
                return None
            
            return cache_data.get("content")
        except Exception:
            # If cache file is corrupted, delete it
            if cache_file.exists():
                cache_file.unlink()
            return None
    
    def set(self, cache_key: str, content: str) -> None:
        """Store content in cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        cache_data = {
            "content": content,
            "cached_at": datetime.now().isoformat(),
            "cache_key": cache_key,
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
        except Exception:
            # If cache write fails, continue without cache
            pass
    
    def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache files. If pattern provided, only clear matching files."""
        cleared = 0
        if pattern:
            for cache_file in self.cache_dir.glob(f"{pattern}*.json"):
                cache_file.unlink()
                cleared += 1
        else:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                cleared += 1
        return cleared

