"""Background worker thread for non-blocking Ren'Py project scanning."""

import time
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QThread, Signal

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.engine.runner import RuleRunner
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.project import RenPyProject
from renpy_inspector.core.parser.project_parser import ProjectParser
from renpy_inspector.core.scanner.file_scanner import FileScanner
from renpy_inspector.core.scanner.validator import ProjectValidator


class ScanWorker(QThread):
    """Executes the validation, scanning, AST parsing, and rule analysis in a background thread."""

    progress_changed = Signal(int, str)  # percent (0-100), message
    scan_finished = Signal(object, list, float)  # RenPyProject, List[Issue], duration_sec
    scan_failed = Signal(str)  # error_message

    def __init__(self, target_path: Path, parent: Optional[object] = None) -> None:
        super().__init__(parent)
        self.target_path = Path(target_path)
        self._is_cancelled = False

    def cancel(self) -> None:
        """Requests cancellation of the running scan."""
        self._is_cancelled = True

    def run(self) -> None:
        """Main worker execution sequence."""
        start_time = time.perf_counter()
        try:
            # Step 1: Validation
            self.progress_changed.emit(10, "Validating Ren'Py project structure...")
            if self._is_cancelled:
                return

            validation = ProjectValidator.validate(self.target_path)
            if not validation.is_valid:
                reasons = "; ".join(validation.errors)
                self.scan_failed.emit(f"Invalid Ren'Py project: {reasons}")
                return

            if validation.game_path is None:
                self.scan_failed.emit("Could not locate game/ directory.")
                return

            project_name = (
                self.target_path.name
                if self.target_path.name.lower() != "game"
                else self.target_path.parent.name
            )
            project = RenPyProject(
                name=project_name,
                root_path=validation.root_path,
                game_path=validation.game_path,
            )

            # Step 2: File Scanning & Asset Catalog
            self.progress_changed.emit(30, "Discovering and cataloging project assets...")
            if self._is_cancelled:
                return

            scanner = FileScanner()
            catalog = scanner.scan(validation.game_path)

            # Step 3: AST Parsing & Symbol Extraction
            self.progress_changed.emit(60, "Parsing Ren'Py scripts and extracting AST symbols...")
            if self._is_cancelled:
                return

            project_parser = ProjectParser()
            parsed_proj = project_parser.parse_project(
                game_directory=validation.game_path,
                catalog=catalog,
            )

            # Step 4: Rule Engine Analysis
            self.progress_changed.emit(80, "Executing QA static analysis rules...")
            if self._is_cancelled:
                return

            context = ProjectContext.build(
                project=project,
                catalog=catalog,
                parsed_project=parsed_proj,
            )

            def on_rule_progress(rule_title: str, current: int, total: int) -> None:
                if self._is_cancelled:
                    return
                pct = 80 + int((current / max(1, total)) * 18)
                self.progress_changed.emit(
                    pct, f"Evaluating rule {current}/{total}: {rule_title}..."
                )

            runner = RuleRunner()
            issues: List[Issue] = runner.run(context, progress_callback=on_rule_progress)

            if self._is_cancelled:
                return

            duration = round(time.perf_counter() - start_time, 3)
            self.progress_changed.emit(100, "Inspection complete.")
            self.scan_finished.emit(project, issues, duration)

        except Exception as exc:
            self.scan_failed.emit(f"Unexpected error during scan: {exc}")
