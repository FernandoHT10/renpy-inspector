"""JSON report exporter with versioned schema for Ren'Py Inspector."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence, Union

from renpy_inspector.core.models.enums import Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.project import RenPyProject


class JsonReporter:
    """Serializes inspection results into a structured, machine-readable JSON document."""

    SCHEMA_VERSION = "1.0.0"

    @classmethod
    def generate_data(
        cls,
        project: RenPyProject,
        issues: Sequence[Issue],
        scan_duration_seconds: float = 0.0,
        extra_metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Build the raw dictionary structure for the report."""
        severity_counts = {
            Severity.CRITICAL.value: 0,
            Severity.ERROR.value: 0,
            Severity.WARNING.value: 0,
            Severity.INFO.value: 0,
        }
        category_counts: dict[str, int] = {}

        serialized_issues = []
        for issue in issues:
            severity_counts[issue.severity.value] = severity_counts.get(issue.severity.value, 0) + 1
            cat_name = issue.category.value
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
            serialized_issues.append(issue.to_dict())

        return {
            "schema_version": cls.SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scan_duration_seconds": round(scan_duration_seconds, 3),
            "project": project.to_dict(),
            "summary": {
                "total_issues": len(issues),
                "by_severity": severity_counts,
                "by_category": category_counts,
            },
            "issues": serialized_issues,
            "metadata": extra_metadata or {},
        }

    @classmethod
    def export(
        cls,
        output_path: Union[str, Path],
        project: RenPyProject,
        issues: Sequence[Issue],
        scan_duration_seconds: float = 0.0,
        extra_metadata: Optional[dict[str, Any]] = None,
        indent: int = 2,
    ) -> Path:
        """Write structured JSON report to disk."""
        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        data = cls.generate_data(
            project=project,
            issues=issues,
            scan_duration_seconds=scan_duration_seconds,
            extra_metadata=extra_metadata,
        )

        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)

        return target
