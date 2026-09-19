"""JSON report exporter with versioned schema for Ren'Py Inspector."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence, Union

from renpy_inspector.core.models.analysis import AnalysisResult
from renpy_inspector.core.models.enums import Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.project import RenPyProject


class JsonReporter:
    """Serializes inspection results into a structured, machine-readable JSON document."""

    SCHEMA_VERSION = "1.0.0"
    SCHEMA_VERSION_V2 = "2.0.0"

    @classmethod
    def generate_data(
        cls,
        project: Optional[RenPyProject] = None,
        issues: Optional[Sequence[Issue]] = None,
        scan_duration_seconds: float = 0.0,
        extra_metadata: Optional[dict[str, Any]] = None,
        *,
        analysis_result: Optional[AnalysisResult] = None,
    ) -> dict[str, Any]:
        """Build the raw dictionary structure for the report."""
        if analysis_result is not None:
            eff_project = analysis_result.project or project
            eff_issues = analysis_result.issues
            eff_duration = analysis_result.scan_duration_seconds
            schema_ver = cls.SCHEMA_VERSION_V2
        else:
            eff_project = project
            eff_issues = tuple(issues or ())
            eff_duration = scan_duration_seconds
            schema_ver = cls.SCHEMA_VERSION

        severity_counts = {
            Severity.CRITICAL.value: 0,
            Severity.ERROR.value: 0,
            Severity.WARNING.value: 0,
            Severity.INFO.value: 0,
        }
        category_counts: dict[str, int] = {}

        serialized_issues = []
        for issue in eff_issues:
            severity_counts[issue.severity.value] = severity_counts.get(issue.severity.value, 0) + 1
            cat_name = issue.category.value
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
            serialized_issues.append(issue.to_dict())

        data: dict[str, Any] = {
            "schema_version": schema_ver,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scan_duration_seconds": round(eff_duration, 3),
            "project": eff_project.to_dict() if eff_project else None,
            "summary": {
                "total_issues": len(eff_issues),
                "by_severity": severity_counts,
                "by_category": category_counts,
            },
            "issues": serialized_issues,
            "metadata": extra_metadata or {},
        }

        if analysis_result is not None:
            data["status"] = analysis_result.status.value
            data["is_clean"] = analysis_result.is_clean
            data["coverage"] = analysis_result.coverage.to_dict()
            data["diagnostics"] = [d.to_dict() for d in analysis_result.diagnostics]
            data["rule_failures"] = [rf.to_dict() for rf in analysis_result.rule_failures]
            data["parse_failures"] = [pf.to_dict() for pf in analysis_result.parse_failures]
            data["scan_errors"] = [se.to_dict() for se in analysis_result.scan_errors]

        return data

    @classmethod
    def export(
        cls,
        output_path: Union[str, Path],
        project: Optional[RenPyProject] = None,
        issues: Optional[Sequence[Issue]] = None,
        scan_duration_seconds: float = 0.0,
        extra_metadata: Optional[dict[str, Any]] = None,
        indent: int = 2,
        *,
        analysis_result: Optional[AnalysisResult] = None,
    ) -> Path:
        """Write structured JSON report to disk."""
        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        data = cls.generate_data(
            project=project,
            issues=issues,
            scan_duration_seconds=scan_duration_seconds,
            extra_metadata=extra_metadata,
            analysis_result=analysis_result,
        )

        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)

        return target
