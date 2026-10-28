"""
core/kb/loaders/__init__.py
Registry of data loaders.
"""

from typing import Dict, Type
from core.kb.loaders.base import BaseDataLoader
from core.kb.loaders.excel_loader import ExcelLoader
from core.kb.loaders.json_loader import JsonCatalogLoader

LOADER_REGISTRY: Dict[str, Type[BaseDataLoader]] = {
    "excel": ExcelLoader,
    "xlsx": ExcelLoader,
    "json": JsonCatalogLoader,
    "json_catalog": JsonCatalogLoader,
    "yaml": JsonCatalogLoader,
    "yaml_catalog": JsonCatalogLoader,
}

def get_loader(loader_type: str) -> BaseDataLoader:
    cls = LOADER_REGISTRY.get(loader_type.lower())
    if not cls:
        raise ValueError(f"Unknown loader type: {loader_type}. Supported: {list(LOADER_REGISTRY.keys())}")
    return cls()
