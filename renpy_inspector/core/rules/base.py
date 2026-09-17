"""Base abstract class for all static analysis rules."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from renpy_inspector.core.license.tier import Tier
from renpy_inspector.core.models.enums import Category, Confidence, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.location import Location

if TYPE_CHECKING:
    from renpy_inspector.core.engine.context import ProjectContext


class BaseRule(ABC):
    """Abstract base class for Ren'Py Inspector analysis rules."""

    rule_id: str
    title: str
    category: Category
    default_severity: Severity
    description: str
    min_tier: Tier = Tier.FREE

    @abstractmethod
    def analyze(self, context: "ProjectContext") -> list[Issue]:
        """Inspect the ProjectContext and return any detected issues."""

    def create_issue(
        self,
        message: str,
        location: Location,
        suggestion: str,
        severity: Optional[Severity] = None,
        confidence: Confidence = Confidence.CERTAIN,
        metadata: Optional[dict] = None,
        custom_title: Optional[str] = None,
    ) -> Issue:
        """Helper to create a well-formed Issue with the rule's defaults."""
        return Issue.create(
            rule_id=self.rule_id,
            severity=severity or self.default_severity,
            category=self.category,
            title=custom_title or self.title,
            message=message,
            location=location,
            suggestion=suggestion,
            confidence=confidence,
            metadata=metadata or {},
        )


# Backward compatibility alias
Rule = BaseRule

