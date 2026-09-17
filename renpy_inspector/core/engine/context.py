"""Context model holding cross-referenced project symbols and asset indices."""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from renpy_inspector.core.models.asset import AssetInfo
from renpy_inspector.core.models.enums import AssetType
from renpy_inspector.core.models.project import RenPyProject
from renpy_inspector.core.models.symbols import (
    AudioReference,
    CallReference,
    DialogueLine,
    ImageDefinition,
    InitStatement,
    JumpReference,
    LabelSymbol,
    MenuBlock,
    PythonBlock,
    ScreenDefinition,
    TranslateBlock,
    UnreachableStatement,
    VariableDeclaration,
)
from renpy_inspector.core.parser.result import ParsedProject
from renpy_inspector.core.scanner.asset_catalog import AssetCatalog

# Ren'Py built-in special lifecycle labels (from official Ren'Py documentation)
BUILTIN_RENPY_LABELS = frozenset(
    {
        "start",
        "quit",
        "main_menu",
        "after_load",
        "before_load",
        "splashscreen",
        "before_main_menu",
        "after_warp",
        "hide_windows",
        "main_menu_screen",
        "load_screen",
        "save_screen",
        "preferences_screen",
        "joystick_preferences_screen",
    }
)

# Ren'Py built-in special and conventional screens (from official Ren'Py documentation)
BUILTIN_RENPY_SCREENS = frozenset(
    {
        "say",
        "choice",
        "main_menu",
        "navigation",
        "file_slots",
        "save",
        "load",
        "preferences",
        "history",
        "help",
        "confirm",
        "yesno_prompt",
        "input",
        "notify",
        "quick_menu",
        "nvl",
        "nvl_choice",
        "game_menu",
        "about",
        "keyboard_help",
        "mouse_help",
        "gamepad_help",
        "skip_indicator",
        "ctc",
        "bubble",
    }
)


RE_IMAGE_TAG = re.compile(r"\{image=([^}]+)\}")


@dataclass
class ProjectContext:
    """Precomputed symbol and asset index for high-performance, deterministic rule execution."""

    project: RenPyProject
    catalog: AssetCatalog
    parsed_project: ParsedProject

    # Precomputed indices
    labels_by_name: dict[str, list[LabelSymbol]] = field(default_factory=lambda: defaultdict(list))
    defined_labels: set[str] = field(default_factory=set)
    local_labels_by_scope: dict[str, set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )

    all_jumps: list[JumpReference] = field(default_factory=list)
    all_calls: list[CallReference] = field(default_factory=list)
    all_images: list[ImageDefinition] = field(default_factory=list)
    all_audios: list[AudioReference] = field(default_factory=list)
    audio_by_filename: dict[str, AssetInfo] = field(default_factory=dict)
    audio_by_stem: dict[str, AssetInfo] = field(default_factory=dict)
    all_variables: list[VariableDeclaration] = field(default_factory=list)
    all_translations: list[TranslateBlock] = field(default_factory=list)
    all_python_blocks: list[PythonBlock] = field(default_factory=list)
    all_screens: list[ScreenDefinition] = field(default_factory=list)
    defined_screens: set[str] = field(default_factory=set)
    screens_by_name: dict[str, list[ScreenDefinition]] = field(
        default_factory=lambda: defaultdict(list)
    )
    screens_by_name_and_variant: dict[tuple[str, Optional[str]], list[ScreenDefinition]] = field(
        default_factory=lambda: defaultdict(list)
    )
    all_menus: list[MenuBlock] = field(default_factory=list)
    all_dialogues: list[DialogueLine] = field(default_factory=list)
    all_unreachables: list[UnreachableStatement] = field(default_factory=list)

    defines_by_name: dict[str, list[VariableDeclaration]] = field(
        default_factory=lambda: defaultdict(list)
    )
    defaults_by_name: dict[str, list[VariableDeclaration]] = field(
        default_factory=lambda: defaultdict(list)
    )
    translations_by_lang: dict[str, list[TranslateBlock]] = field(
        default_factory=lambda: defaultdict(list)
    )

    # Set of words/tokens found across script sources for unused asset analysis
    script_token_pool: set[str] = field(default_factory=set)
    # Audio channels explicitly registered via renpy.music.register_channel
    registered_audio_channels: set[str] = field(default_factory=set)
    all_init_statements: list[InitStatement] = field(default_factory=list)
    custom_text_tags: set[str] = field(default_factory=set)
    custom_self_closing_text_tags: set[str] = field(default_factory=set)

    @classmethod
    def build(
        cls,
        project: RenPyProject,
        catalog: AssetCatalog,
        parsed_project: ParsedProject,
    ) -> "ProjectContext":
        """Construct and index all project symbols for rule execution."""
        ctx = cls(
            project=project,
            catalog=catalog,
            parsed_project=parsed_project,
        )
        ctx._index_symbols()
        return ctx

    def _index_symbols(self) -> None:
        """Populate symbol tables and cross-reference maps."""
        # Include built-in Ren'Py labels and screens
        self.defined_labels.update(BUILTIN_RENPY_LABELS)
        self.defined_screens.update(BUILTIN_RENPY_SCREENS)

        def add_token(token: str) -> None:
            clean = token.strip()
            if not clean:
                return
            self.script_token_pool.add(clean)
            clean_lower = clean.lower()
            self.script_token_pool.add(clean_lower)
            posix = clean.replace("\\", "/")
            self.script_token_pool.add(posix)
            self.script_token_pool.add(posix.lower())

            p = Path(posix)
            fname = p.name
            if fname:
                self.script_token_pool.add(fname)
                self.script_token_pool.add(fname.lower())
            stem = p.stem
            if stem:
                self.script_token_pool.add(stem)
                self.script_token_pool.add(stem.lower())
                self.script_token_pool.add(stem.replace("_", " "))
                self.script_token_pool.add(stem.replace("_", " ").lower())
                self.script_token_pool.add(stem.replace(" ", "_"))
                self.script_token_pool.add(stem.replace(" ", "_").lower())
            if "_" in clean:
                self.script_token_pool.add(clean.replace("_", " "))
                self.script_token_pool.add(clean.replace("_", " ").lower())
            if " " in clean:
                self.script_token_pool.add(clean.replace(" ", "_"))
                self.script_token_pool.add(clean.replace(" ", "_").lower())

        for file_result in self.parsed_project.files.values():
            # Index registered audio channels
            for ch in file_result.registered_channels:
                self.registered_audio_channels.add(ch.lower())
                add_token(ch)

            # Index labels
            for lbl in file_result.labels:
                self.labels_by_name[lbl.name].append(lbl)
                self.defined_labels.add(lbl.name)

                if lbl.is_local and lbl.parent_label:
                    # e.g. parent="chapter", name=".choice" -> "chapter.choice"
                    full_local = f"{lbl.parent_label}{lbl.name}"
                    self.defined_labels.add(full_local)
                    self.local_labels_by_scope[lbl.parent_label].add(lbl.name)
                elif not lbl.is_local:
                    self.defined_labels.add(lbl.name)

            # Index screens
            for sc in file_result.screens:
                self.all_screens.append(sc)
                self.defined_screens.add(sc.name)
                self.screens_by_name[sc.name].append(sc)
                self.screens_by_name_and_variant[(sc.name, sc.variant)].append(sc)
                add_token(sc.name)

            # Collect references
            self.all_jumps.extend(file_result.jumps)
            self.all_calls.extend(file_result.calls)
            self.all_images.extend(file_result.images)
            self.all_audios.extend(file_result.audios)
            self.all_variables.extend(file_result.variables)
            self.all_translations.extend(file_result.translations)
            self.all_python_blocks.extend(file_result.python_blocks)
            self.all_menus.extend(file_result.menus)
            self.all_dialogues.extend(file_result.dialogues)
            self.all_unreachables.extend(file_result.unreachables)
            self.all_init_statements.extend(file_result.init_statements)
            self.custom_text_tags.update(file_result.custom_text_tags)
            self.custom_self_closing_text_tags.update(file_result.custom_self_closing_text_tags)

            # Index define and default
            for var in file_result.variables:
                if var.kind == "define":
                    self.defines_by_name[var.name].append(var)
                elif var.kind == "default":
                    self.defaults_by_name[var.name].append(var)

            # Index translations
            for tr in file_result.translations:
                self.translations_by_lang[tr.language].append(tr)

            # Build token pool from script references for asset matching
            for jump in file_result.jumps:
                add_token(jump.target)
            for call in file_result.calls:
                add_token(call.target)
            for img in file_result.images:
                add_token(img.name)
                if img.asset_reference:
                    add_token(img.asset_reference)
            for aud in file_result.audios:
                add_token(aud.target)
            for var in file_result.variables:
                add_token(var.name)
                if var.raw_value:
                    add_token(var.raw_value.strip('"\''))
            for tag in file_result.scenes_and_shows:
                add_token(tag)
                # If tag is composite (e.g. "chel happy"), also index parts
                for part in tag.split():
                    add_token(part)
            for lit in file_result.string_literals:
                add_token(lit)
                if "{image=" in lit:
                    for m_img in RE_IMAGE_TAG.finditer(lit):
                        add_token(m_img.group(1))

        # Index audio and video assets by filename and stem for recursive audio lookup
        for a in self.catalog.get_by_type(AssetType.AUDIO):
            self.audio_by_filename[a.filename.lower()] = a
            self.audio_by_stem[Path(a.filename).stem.lower()] = a
        for a in self.catalog.get_by_type(AssetType.VIDEO):
            self.audio_by_filename[a.filename.lower()] = a
            self.audio_by_stem[Path(a.filename).stem.lower()] = a

    def has_label(self, label_name: str, scope: Optional[str] = None) -> bool:
        """Check whether a label is defined globally or within scope."""
        if label_name.startswith("."):
            if scope:
                full_name = f"{scope}{label_name}"
                return full_name in self.defined_labels
            return False
        return label_name in self.defined_labels

    def resolve_audio_asset(self, audio_target: str) -> Optional[AssetInfo]:
        """Resolve audio path in game/ and game/audio/ with stem tolerance."""
        clean_target = audio_target.strip("\"'").replace("\\", "/")
        clean_target = re.sub(r"^(<[^>]+>\s*)+", "", clean_target)

        # 1. Check exact path in game/
        asset = self.catalog.find_exact(clean_target)
        if asset and asset.asset_type in (AssetType.AUDIO, AssetType.VIDEO):
            return asset

        # 2. Check in game/audio/
        audio_subpath = f"audio/{clean_target}"
        asset_sub = self.catalog.find_exact(audio_subpath)
        if asset_sub and asset_sub.asset_type in (AssetType.AUDIO, AssetType.VIDEO):
            return asset_sub

        # 3. Check case-insensitive match
        matches = self.catalog.find_case_insensitive(clean_target)
        if not matches:
            matches = self.catalog.find_case_insensitive(audio_subpath)

        for m in matches:
            if m.asset_type in (AssetType.AUDIO, AssetType.VIDEO):
                return m

        # 4. Check recursive search in audio directory by filename or extensionless stem
        target_name_lower = Path(clean_target).name.lower()
        target_stem_lower = Path(clean_target).stem.lower()

        found = (
            self.audio_by_filename.get(target_name_lower)
            or self.audio_by_stem.get(target_stem_lower)
        )
        if found:
            return found

        # 5. Try common audio extensions if target had no extension or different extension
        for ext in (".ogg", ".opus", ".mp3", ".wav"):
            candidate = f"{target_stem_lower}{ext}"
            found = self.audio_by_filename.get(candidate)
            if found:
                return found

        return None

