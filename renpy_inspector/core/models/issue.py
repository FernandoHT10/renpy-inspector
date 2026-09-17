"""Issue domain model representing a detected QA problem or warning."""

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from renpy_inspector.core.models.enums import Category, Confidence, Severity
from renpy_inspector.core.models.location import Location


def generate_issue_id(
    rule_id: str,
    file_path: str,
    line_number: Optional[int],
    message: str,
) -> str:
    """Generate a deterministic identifier for issue deduplication and tracking."""
    normalized_line = str(line_number) if line_number is not None else ""
    raw_key = f"{rule_id}|{file_path}|{normalized_line}|{message}"
    return hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Issue:
    """Represents an issue found during static analysis."""

    id: str
    rule_id: str
    severity: Severity
    category: Category
    title: str
    message: str
    location: Location
    suggestion: str
    confidence: Confidence = Confidence.CERTAIN
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        rule_id: str,
        severity: Severity,
        category: Category,
        title: str,
        message: str,
        location: Location,
        suggestion: str,
        confidence: Confidence = Confidence.CERTAIN,
        metadata: Optional[dict[str, Any]] = None,
        custom_id: Optional[str] = None,
    ) -> "Issue":
        """Factory method to construct an Issue with an auto-generated deterministic ID."""
        issue_id = (
            custom_id
            if custom_id
            else generate_issue_id(rule_id, location.file_path, location.line_number, message)
        )
        return cls(
            id=issue_id,
            rule_id=rule_id,
            severity=severity,
            category=category,
            title=title,
            message=message,
            location=location,
            suggestion=suggestion,
            confidence=confidence,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert issue to a JSON-serializable dictionary."""
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "message": self.message,
            "location": self.location.to_dict(),
            "suggestion": self.suggestion,
            "confidence": self.confidence.value,
            "metadata": dict(self.metadata),
        }
