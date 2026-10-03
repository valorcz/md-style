"""
core/diagnostics.py
Structured logging, performance timers, and diagnostic metrics for pipeline troubleshooting.
"""

import sys
import time
from typing import Dict, Any, List

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    BLUE = "\033[38;5;39m"
    GREEN = "\033[38;5;76m"
    YELLOW = "\033[38;5;214m"
    RED = "\033[38;5;196m"
    GRAY = "\033[38;5;245m"
    CYAN = "\033[38;5;51m"
    MAGENTA = "\033[38;5;201m"

    @classmethod
    def disable(cls):
        cls.RESET = ""
        cls.BOLD = ""
        cls.BLUE = ""
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.RED = ""
        cls.GRAY = ""
        cls.CYAN = ""
        cls.MAGENTA = ""

if not sys.stdout.isatty():
    Colors.disable()

class Diagnostics:
    verbose: bool = False
    debug: bool = False

    @classmethod
    def info(cls, msg: str):
        print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}", file=sys.stderr)

    @classmethod
    def success(cls, msg: str):
        print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {Colors.BOLD}{msg}{Colors.RESET}", file=sys.stderr)

    @classmethod
    def warn(cls, msg: str):
        print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {msg}", file=sys.stderr)

    @classmethod
    def error(cls, msg: str):
        print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}", file=sys.stderr)

    @classmethod
    def debug_log(cls, msg: str):
        if cls.debug or cls.verbose:
            print(f"{Colors.GRAY}[DEBUG]{Colors.RESET} {msg}", file=sys.stderr)

logger = Diagnostics

class PipelineTimer:
    def __init__(self):
        self.start_times: Dict[str, float] = {}
        self.durations: Dict[str, float] = {}

    def start(self, stage: str):
        self.start_times[stage] = time.time()

    def stop(self, stage: str) -> float:
        if stage in self.start_times:
            duration = time.time() - self.start_times[stage]
            self.durations[stage] = duration
            return duration
        return 0.0

    def get(self, stage: str) -> float:
        return self.durations.get(stage, 0.0)

class DiagnosticMetrics:
    def __init__(self):
        self.tokens_found: List[Dict[str, Any]] = []
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.online_queries: int = 0
        self.diagrams_rendered: int = 0
        self.ast_replacements: List[Dict[str, Any]] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def record_token(self, token: str, module: str, line: int, resolved: bool, metadata_preview: str, cached: bool = False):
        self.tokens_found.append({
            "token": token,
            "module": module,
            "line": line,
            "resolved": resolved,
            "preview": metadata_preview,
            "cached": cached
        })
        if cached:
            self.cache_hits += 1
        elif resolved:
            self.cache_misses += 1

    def record_ast_replacement(self, elem_type: str, original: str, transformed: str, line: int = 0):
        self.ast_replacements.append({
            "type": elem_type,
            "original": original,
            "transformed": transformed,
            "line": line
        })
