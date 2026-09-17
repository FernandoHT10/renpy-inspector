"""Dynamic custom QA rule plugin discovery and loader (Developer Edition)."""

import importlib.util
import inspect
from pathlib import Path
from typing import List, Optional, Type

from renpy_inspector.core.license.manager import TierManager
from renpy_inspector.core.rules.base import BaseRule


class PluginLoader:
    """Discovers and securely registers external custom rules."""

    def __init__(self, tier_manager: Optional[TierManager] = None) -> None:
        self.tier_manager = tier_manager or TierManager.get_instance()

    def load_plugins_from_directory(self, directory: Path) -> List[BaseRule]:
        """Discovers and instantiates custom Rule classes from Python files in directory."""
        rules: List[BaseRule] = []

        if not self.tier_manager.can_load_plugins():
            return rules

        dir_path = Path(directory)
        if not dir_path.is_dir():
            return rules

        for py_file in dir_path.glob("*.py"):
            if py_file.name.startswith(("_", ".")):
                continue

            try:
                module_name = f"renpy_inspector_plugin_{py_file.stem}"
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Scan module for BaseRule subclasses
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseRule) and obj is not BaseRule:
                        rule_cls: Type[BaseRule] = obj
                        # Instantiate rule
                        rules.append(rule_cls())
            except Exception:
                # Silently ignore broken plugin scripts to avoid crashing the analyzer
                continue

        return rules
