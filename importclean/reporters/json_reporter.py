"""JSON output reporter for importclean."""

from __future__ import annotations

import json
from pathlib import Path

from importclean.models import CleanReport, FileReport


class JsonReporter:
    """Serialize a :class:`CleanReport` to JSON."""

    def to_json(self, report: CleanReport, indent: int = 2) -> str:
        """Return the full report as a JSON string."""
        return json.dumps(self._serialize(report), indent=indent)

    def _serialize(self, report: CleanReport) -> dict:  # type: ignore[type-arg]
        return {
            "summary": report.to_dict(),
            "circular_imports": [str(ci) for ci in report.circular_imports],
            "files": [self._serialize_file(fr) for fr in report.file_reports if fr.has_issues],
        }

    def _serialize_file(self, fr: FileReport) -> dict:  # type: ignore[type-arg]
        return {
            "path": _rel(fr.path),
            "modified": fr.modified,
            "syntax_error": fr.syntax_error,
            "unused": [
                {
                    "line": u.import_info.lineno,
                    "statement": str(u.import_info),
                    "reason": u.reason,
                }
                for u in fr.unused
            ],
            "duplicates": [
                {
                    "original_line": d.original.lineno,
                    "duplicate_line": d.duplicate.lineno,
                    "statement": str(d.original),
                }
                for d in fr.duplicates
            ],
            "heavy": [
                {
                    "line": h.import_info.lineno,
                    "module": h.import_info.module,
                    "suggestion": h.suggestion,
                }
                for h in fr.heavy
            ],
        }


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)
