"""
core/providers/mitre_provider.py
Data provider for MITRE ATT&CK enterprise matrix techniques and tactics.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from core.providers.base import BaseProvider
from core.config import MITRE_DB_PATH
from core.diagnostics import Diagnostics

class MitreProvider(BaseProvider):
    name = "mitre"

    def __init__(self, db_path: Path = MITRE_DB_PATH, allow_online: bool = True):
        super().__init__(cache_file=None, allow_online=allow_online)
        self.db_path = db_path
        self._db: Dict[str, Any] = {}
        self._load_db()

    def _load_db(self):
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self._db = json.load(f)
                Diagnostics.debug_log(f"[MitreProvider] Loaded {len(self._db)} techniques from {self.db_path}")
            except Exception as err:
                Diagnostics.warn(f"[MitreProvider] Failed to load {self.db_path}: {err}")
        else:
            Diagnostics.debug_log(f"[MitreProvider] {self.db_path} does not exist yet. Run scripts/build-mitre-dataset.py to compile.")

    def fetch(self, key: str) -> Optional[Dict[str, Any]]:
        clean_key = key.strip()
        if clean_key in self._db:
            return self._db[clean_key]

        upper_key = clean_key.upper()
        if upper_key in self._db:
            return self._db[upper_key]

        return None
