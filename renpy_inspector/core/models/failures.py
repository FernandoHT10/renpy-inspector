"""Failure and error models for parser, scanner, and rule engine."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuleFailure:
    """Represents an unhandled exception that occurred during rule execution."""

    rule_id: str
    rule_title: str
    error_type: str
    error_message: str
    traceback: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_title": self.rule_title,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback,
        }


@dataclass(frozen=True)
class ParseFailure:
    """Represents an unhandled exception that occurred while parsing a script file."""

    file_path: str
    error_type: str
    error_message: str
    traceback: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback,
        }


@dataclass(frozen=True)
class ScanError:
    """Represents an inaccessible file or directory encountered during filesystem scanning."""

    path: str
    operation: str
    error_type: str
    error_message: str
    is_directory: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "operation": self.operation,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "is_directory": self.is_directory,
        }
