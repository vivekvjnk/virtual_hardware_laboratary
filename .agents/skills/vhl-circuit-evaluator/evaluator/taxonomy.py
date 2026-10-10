"""
Taxonomy module: Scalable, regex-based error classification engine.
Maps raw compiler errors to structured diagnostic categories.
"""

from __future__ import annotations

import re
from typing import List, Tuple, Pattern
from .models import DiagnosticError, ErrorCategory


class ErrorTaxonomy:
    """Registry of rules mapping compiler lines to diagnostic categories."""

    def __init__(self):
        self.rules: List[Tuple[ErrorCategory, Pattern[str]]] = []
        self._register_default_rules()

    def register_rule(self, category: ErrorCategory, pattern: str | Pattern[str]):
        if isinstance(pattern, str):
            compiled = re.compile(pattern, re.IGNORECASE)
        else:
            compiled = pattern
        self.rules.append((category, compiled))

    def _register_default_rules(self):
        # 1. UNRESOLVED_IMPORT
        self.register_rule(
            ErrorCategory.UNRESOLVED_IMPORT,
            r"(?:cannot find module|unable to resolve|failed to resolve|module not found).*?['\"]([^'\"]+)['\"]",
        )
        self.register_rule(
            ErrorCategory.UNRESOLVED_IMPORT,
            r"Cannot find module\s+['\"][^'\"]+['\"]",
        )
        self.register_rule(
            ErrorCategory.UNRESOLVED_IMPORT,
            r"ERR_MODULE_NOT_FOUND",
        )

        # 2. FOOTPRINT_ERROR
        self.register_rule(
            ErrorCategory.FOOTPRINT_ERROR,
            r"No footprint specified for component",
        )
        self.register_rule(
            ErrorCategory.FOOTPRINT_ERROR,
            r"Invalid footprint|footprinter.*failed|unknown footprint",
        )
        self.register_rule(
            ErrorCategory.FOOTPRINT_ERROR,
            r"ftype=.*?reference designator should start with",
        )

        # 3. UNROUTED_PORT
        self.register_rule(
            ErrorCategory.UNROUTED_PORT,
            r"Port\s+\w+\s+on\s+.*?is missing a trace",
        )
        self.register_rule(
            ErrorCategory.UNROUTED_PORT,
            r"unrouted port|missing trace|floating net",
        )

        # 4. COMPONENT_PIN_MISMATCH
        self.register_rule(
            ErrorCategory.COMPONENT_PIN_MISMATCH,
            r"Property\s+['\"]pin\d+['\"]\s+does not exist",
        )
        self.register_rule(
            ErrorCategory.COMPONENT_PIN_MISMATCH,
            r"pinLabels.*?mismatch|unknown pin\s+['\"]?\w+['\"]?",
        )

        # 5. SYNTAX_ERROR
        self.register_rule(
            ErrorCategory.SYNTAX_ERROR,
            r"SyntaxError|Unexpected token|JSX element.*?has no corresponding closing tag",
        )
        self.register_rule(
            ErrorCategory.SYNTAX_ERROR,
            r"Expected\s+['\"][^'\"]+['\"]\s+but found",
        )

        # 6. TYPE_ERROR
        self.register_rule(
            ErrorCategory.TYPE_ERROR,
            r"TS\d{4}:|Type\s+['\"][^'\"]+['\"]\s+is not assignable",
        )

        # 7. BUILD_FAILURE
        self.register_rule(
            ErrorCategory.BUILD_FAILURE,
            r"Build completed with errors|circuit build errors occurred|Build failed with",
        )

    def classify_line(self, line: str) -> List[DiagnosticError]:
        matches: List[DiagnosticError] = []
        for category, pattern in self.rules:
            if pattern.search(line):
                # Extract file and line number if present
                loc_match = re.search(r"([\w./\\-]+\.tsx?):(\d+)(?::(\d+))?", line)
                file_path = loc_match.group(1) if loc_match else None
                line_no = int(loc_match.group(2)) if loc_match else None

                matches.append(
                    DiagnosticError(
                        category=category,
                        message=line.strip(),
                        line_number=line_no,
                        file_path=file_path,
                        raw_line=line,
                    )
                )
        return matches

    def classify_logs(self, logs: List[str]) -> List[DiagnosticError]:
        diagnostics: List[DiagnosticError] = []
        seen = set()
        for line in logs:
            for diag in self.classify_line(line):
                key = (diag.category.value, diag.message)
                if key not in seen:
                    seen.add(key)
                    diagnostics.append(diag)
        return diagnostics
