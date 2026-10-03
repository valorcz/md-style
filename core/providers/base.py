"""
core/providers/base.py
Abstract base provider with standardized persistent file caching and in-memory lookup.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from core.diagnostics import Diagnostics

class BaseProvider(ABC):
    """Abstract base class for all security intelligence data sources."""
    name: str = "base"

    def __init__(self, cache_file: Optional[Path] = None, allow_online: bool = True):
        self.cache_file = cache_file
        self.allow_online = allow_online
        self._memory_cache: Dict[str, Any] = {}
        self._dirty = False
        self._load_cache()

    def _load_cache(self):
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._memory_cache = json.load(f)
                Diagnostics.debug_log(f"[{self.name}] Loaded {len(self._memory_cache)} cached entries from {self.cache_file}")
            except Exception as err:
                Diagnostics.warn(f"[{self.name}] Failed to load cache from {self.cache_file}: {err}")
                self._memory_cache = {}

    def save_cache(self):
        if self.cache_file and self._dirty:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(self._memory_cache, f, indent=2, ensure_ascii=False)
                self._dirty = False
                Diagnostics.debug_log(f"[{self.name}] Flushed {len(self._memory_cache)} entries to {self.cache_file}")
            except Exception as err:
                Diagnostics.warn(f"[{self.name}] Failed to save cache: {err}")

    @abstractmethod
    def fetch(self, key: str) -> Optional[Dict[str, Any]]:
        """Fetch item from primary source (local DB or API)."""
        pass

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Lookup item from cache first, then fetch if allowed."""
        if not key:
            return None
        
        lookup_key = key.strip()
        if lookup_key in self._memory_cache:
            return self._memory_cache[lookup_key]

        upper_key = lookup_key.upper()
        if upper_key in self._memory_cache:
            return self._memory_cache[upper_key]

        # Fetch from underlying source
        result = self.fetch(lookup_key)
        if result:
            self._memory_cache[lookup_key] = result
            self._dirty = True
            return result

        return None
