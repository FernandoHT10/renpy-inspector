"""Code rules package."""

from renpy_inspector.core.rules.code.broken_call import BrokenCallRule
from renpy_inspector.core.rules.code.broken_jump import BrokenJumpRule
from renpy_inspector.core.rules.code.conflicting_define_default import (
    ConflictingDefineDefaultRule,
)
from renpy_inspector.core.rules.code.define_persistent import DefinePersistentRule
from renpy_inspector.core.rules.code.duplicate_label import DuplicateLabelRule
from renpy_inspector.core.rules.code.duplicate_screen import DuplicateScreenRule
from renpy_inspector.core.rules.code.empty_menu import EmptyMenuRule
from renpy_inspector.core.rules.code.invalid_init_priority import (
    InvalidInitPriorityRule,
)
from renpy_inspector.core.rules.code.shadow_builtin import ShadowBuiltinRule
from renpy_inspector.core.rules.code.unclosed_text_tags import UnclosedTextTagsRule
from renpy_inspector.core.rules.code.undefined_screen import UndefinedScreenRule
from renpy_inspector.core.rules.code.unreachable_code import UnreachableCodeRule
from renpy_inspector.core.rules.code.unused_label import UnusedLabelRule

__all__ = [
    "BrokenJumpRule",
    "BrokenCallRule",
    "DuplicateLabelRule",
    "ConflictingDefineDefaultRule",
    "UnusedLabelRule",
    "UndefinedScreenRule",
    "ShadowBuiltinRule",
    "UnreachableCodeRule",
    "DefinePersistentRule",
    "EmptyMenuRule",
    "DuplicateScreenRule",
    "UnclosedTextTagsRule",
    "InvalidInitPriorityRule",
]
