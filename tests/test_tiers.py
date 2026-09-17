"""Unit tests for Phase 8 Commercial Extensibility and Tier Management."""

from pathlib import Path

from renpy_inspector.core.license.manager import TierManager
from renpy_inspector.core.license.tier import Tier
from renpy_inspector.core.plugins.loader import PluginLoader


def test_tier_comparison_and_from_str():
    assert Tier.FREE < Tier.PRO < Tier.DEV
    assert Tier.PRO >= Tier.FREE
    assert Tier.DEV >= Tier.PRO

    assert Tier.from_str("pro") == Tier.PRO
    assert Tier.from_str("PROFESSIONAL") == Tier.PRO
    assert Tier.from_str("dev") == Tier.DEV
    assert Tier.from_str("enterprise") == Tier.DEV
    assert Tier.from_str("unknown") == Tier.FREE


def test_tier_manager_capabilities():
    mgr_free = TierManager(override_tier=Tier.FREE)
    assert mgr_free.can_export_html() is False
    assert mgr_free.can_export_json() is False
    assert mgr_free.can_load_plugins() is False
    assert mgr_free.is_rule_allowed(Tier.FREE) is True
    assert mgr_free.is_rule_allowed(Tier.PRO) is False

    mgr_pro = TierManager(override_tier=Tier.PRO)
    assert mgr_pro.can_export_html() is True
    assert mgr_pro.can_export_json() is True
    assert mgr_pro.can_load_plugins() is False
    assert mgr_pro.is_rule_allowed(Tier.FREE) is True
    assert mgr_pro.is_rule_allowed(Tier.PRO) is True
    assert mgr_pro.is_rule_allowed(Tier.DEV) is False

    mgr_dev = TierManager(override_tier=Tier.DEV)
    assert mgr_dev.can_export_html() is True
    assert mgr_dev.can_export_json() is True
    assert mgr_dev.can_load_plugins() is True
    assert mgr_dev.is_rule_allowed(Tier.DEV) is True


def test_plugin_loader_security_and_discovery(tmp_path: Path):
    plugins_dir = tmp_path / "custom_plugins"
    plugins_dir.mkdir()

    # Create a custom rule file
    plugin_code = """
from renpy_inspector.core.rules.base import BaseRule
from renpy_inspector.core.models.enums import Category, Severity

class CustomStudioRule(BaseRule):
    rule_id = "CUSTOM-001"
    title = "Custom Studio Check"
    category = Category.CODE
    default_severity = Severity.WARNING
    description = "Custom in-house rule."

    def analyze(self, context):
        return []
"""
    (plugins_dir / "my_custom_rule.py").write_text(plugin_code, encoding="utf-8")

    # When Free Tier: loader returns empty list
    free_mgr = TierManager(override_tier=Tier.FREE)
    free_loader = PluginLoader(tier_manager=free_mgr)
    assert free_loader.load_plugins_from_directory(plugins_dir) == []

    # When Dev Tier: rule is discovered and loaded
    dev_mgr = TierManager(override_tier=Tier.DEV)
    dev_loader = PluginLoader(tier_manager=dev_mgr)
    loaded_rules = dev_loader.load_plugins_from_directory(plugins_dir)

    assert len(loaded_rules) == 1
    assert loaded_rules[0].rule_id == "CUSTOM-001"
    assert loaded_rules[0].title == "Custom Studio Check"
