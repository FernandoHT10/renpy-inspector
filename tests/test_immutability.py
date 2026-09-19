"""Tests for Problem #6: Immutability of ProjectContext and Hardening of RuleRegistry."""

from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType

import pytest

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.engine.registry import RuleRegistry
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.location import Location
from renpy_inspector.core.models.symbols import JumpReference, LabelSymbol
from renpy_inspector.core.rules.base import BaseRule
from renpy_inspector.core.rules.code.broken_jump import BrokenJumpRule
from tests.test_rules import create_test_context


def _build_sample_context(tmp_path: Path) -> ProjectContext:
    scripts = {
        "script.rpy": """
label start:
    jump chapter_1

label chapter_1:
    $ renpy.jump("start")
    play music "theme.ogg"
    return
"""
    }
    dummy_assets = ["audio/theme.ogg"]
    return create_test_context(tmp_path, scripts, dummy_assets=dummy_assets)


# 1. ProjectContext attribute immutability
def test_project_context_attribute_reassignment_raises_frozen_error(tmp_path: Path):
    """Attempting to assign any attribute on ProjectContext must raise FrozenInstanceError."""
    ctx = _build_sample_context(tmp_path)

    with pytest.raises(FrozenInstanceError):
        ctx.defined_labels = frozenset({"hacked"})  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        ctx.all_jumps = ()  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        ctx.labels_by_name = MappingProxyType({})  # type: ignore[misc]


# 2. Sequence immutability (tuple)
def test_project_context_sequences_are_immutable_tuples(tmp_path: Path):
    """All sequence attributes must be immutable tuples that forbid mutations."""
    ctx = _build_sample_context(tmp_path)

    assert isinstance(ctx.all_jumps, tuple)
    assert isinstance(ctx.all_calls, tuple)
    assert isinstance(ctx.all_images, tuple)
    assert isinstance(ctx.all_audios, tuple)
    assert isinstance(ctx.all_variables, tuple)
    assert isinstance(ctx.all_screens, tuple)
    assert isinstance(ctx.all_menus, tuple)
    assert isinstance(ctx.all_dialogues, tuple)
    assert isinstance(ctx.all_unreachables, tuple)
    assert isinstance(ctx.all_init_statements, tuple)

    loc = Location(file_path="game/script.rpy", line_number=10)
    fake_jump = JumpReference(target="fake", location=loc)

    with pytest.raises(AttributeError):
        ctx.all_jumps.append(fake_jump)  # type: ignore[attr-defined]

    with pytest.raises(AttributeError):
        ctx.all_audios.pop()  # type: ignore[attr-defined]

    with pytest.raises(TypeError):
        ctx.all_jumps[0] = fake_jump  # type: ignore[index]


# 3. Set immutability (frozenset)
def test_project_context_sets_are_frozensets(tmp_path: Path):
    """All set attributes must be frozensets that forbid additions or removals."""
    ctx = _build_sample_context(tmp_path)

    assert isinstance(ctx.defined_labels, frozenset)
    assert isinstance(ctx.defined_screens, frozenset)
    assert isinstance(ctx.script_token_pool, frozenset)
    assert isinstance(ctx.registered_audio_channels, frozenset)
    assert isinstance(ctx.custom_text_tags, frozenset)
    assert isinstance(ctx.custom_self_closing_text_tags, frozenset)

    with pytest.raises(AttributeError):
        ctx.defined_labels.add("injected_label")  # type: ignore[attr-defined]

    with pytest.raises(AttributeError):
        ctx.defined_labels.remove("start")  # type: ignore[attr-defined]


# 4. Mapping immutability (MappingProxyType outer)
def test_project_context_mappings_are_read_only_proxies(tmp_path: Path):
    """All mapping attributes must be MappingProxyType that forbid key assignments or pops."""
    ctx = _build_sample_context(tmp_path)

    assert isinstance(ctx.labels_by_name, MappingProxyType)
    assert isinstance(ctx.local_labels_by_scope, MappingProxyType)
    assert isinstance(ctx.screens_by_name, MappingProxyType)
    assert isinstance(ctx.screens_by_name_and_variant, MappingProxyType)
    assert isinstance(ctx.defines_by_name, MappingProxyType)
    assert isinstance(ctx.defaults_by_name, MappingProxyType)
    assert isinstance(ctx.translations_by_lang, MappingProxyType)
    assert isinstance(ctx.audio_namespace_symbols, MappingProxyType)

    with pytest.raises(TypeError):
        ctx.labels_by_name["injected"] = ()  # type: ignore[index]

    with pytest.raises(AttributeError):
        ctx.labels_by_name.pop("start")  # type: ignore[attr-defined]

    with pytest.raises(AttributeError):
        ctx.labels_by_name.clear()  # type: ignore[attr-defined]


# 5. Nested collection immutability (recursively frozen values)
def test_project_context_mapping_values_are_recursively_frozen(tmp_path: Path):
    """Values inside mappings must be immutable tuples or frozensets, preventing nested mutation."""
    ctx = _build_sample_context(tmp_path)

    start_labels = ctx.labels_by_name["start"]
    assert isinstance(start_labels, tuple)

    loc = Location(file_path="game/script.rpy", line_number=99)
    injected_sym = LabelSymbol(name="start", location=loc)

    with pytest.raises(AttributeError):
        start_labels.append(injected_sym)  # type: ignore[attr-defined]

    with pytest.raises(TypeError):
        start_labels[0] = injected_sym  # type: ignore[index]


# 6. Audio resolution encapsulation
def test_resolve_audio_private_cache_and_determinism(tmp_path: Path):
    """resolve_audio must return deterministic memoized results without leaking mutable state."""
    ctx = _build_sample_context(tmp_path)

    assert len(ctx.all_audios) >= 1
    ref = ctx.all_audios[0]

    # Precomputed resolution
    res1 = ctx.resolve_audio(ref)
    res2 = ctx.resolve_audio(ref)
    assert res1 is res2

    # Internal cache is not exposed in public representation
    ctx_repr = repr(ctx)
    assert "_audio_cache" not in ctx_repr


# 7. RuleRegistry duplicate rejection
class DummyRuleA(BaseRule):
    rule_id = "TEST-DUP-001"
    title = "Rule A"
    category = Category.CODE
    default_severity = Severity.WARNING
    description = "Test rule"

    def analyze(self, context):
        return []


class DummyRuleB(BaseRule):
    rule_id = "TEST-DUP-001"  # Same ID!
    title = "Rule B (Collision)"
    category = Category.CODE
    default_severity = Severity.ERROR
    description = "Test colliding rule"

    def analyze(self, context):
        return []


def test_rule_registry_rejects_duplicate_ids_without_allow_override():
    """Registering a rule with an existing ID must raise ValueError unless allow_override=True."""
    registry = RuleRegistry()
    registry.register(DummyRuleA())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(DummyRuleB())

    # Still retains original Rule A
    rule = registry.get_rule("TEST-DUP-001")
    assert rule.title == "Rule A"


def test_rule_registry_allows_override_when_explicit():
    """Registering a duplicate rule with allow_override=True successfully replaces the instance."""
    registry = RuleRegistry()
    registry.register(BrokenJumpRule())
    registry.register(DummyRuleA())

    rule_ids_before = [r.rule_id for r in registry.get_all_rules()]

    # Explicit override
    registry.register(DummyRuleB(), allow_override=True, enabled=False)

    rule_ids_after = [r.rule_id for r in registry.get_all_rules()]
    assert rule_ids_before == rule_ids_after  # Position/order is preserved

    updated_rule = registry.get_rule("TEST-DUP-001")
    assert updated_rule.title == "Rule B (Collision)"
    assert not registry.is_enabled("TEST-DUP-001")


def test_rule_registry_set_enabled_validates_rule_id():
    """set_enabled must raise KeyError when given an unknown rule ID."""
    registry = RuleRegistry()
    registry.register(BrokenJumpRule())

    # Unknown ID raises KeyError
    with pytest.raises(KeyError, match="Cannot configure unknown rule ID 'NONEXISTENT-RULE'"):
        registry.set_enabled("NONEXISTENT-RULE", True)

    # Valid ID succeeds
    registry.set_enabled("RPY-CODE-001", False)
    assert not registry.is_enabled("RPY-CODE-001")
    registry.set_enabled("RPY-CODE-001", True)
    assert registry.is_enabled("RPY-CODE-001")
