"""Context model holding cross-referenced project symbols and asset indices."""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Optional

from renpy_inspector.core.models.asset import AssetInfo
from renpy_inspector.core.models.enums import AssetType
from renpy_inspector.core.models.location import Location
from renpy_inspector.core.models.project import RenPyProject
from renpy_inspector.core.models.resolution import AssetResolution, ResolutionStatus
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

# Ren'Py lifecycle hook labels (engine entry points and callbacks)
LIFECYCLE_HOOK_LABELS = frozenset(
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
BUILTIN_RENPY_LABELS = LIFECYCLE_HOOK_LABELS  # Backward compatibility alias

# Ren'Py common runtime fallback screens provided by engine in renpy/common/
ENGINE_COMMON_SCREENS = frozenset(
    {
        "_confirm",
        "_error",
        "_input",
        "_choice",
        "_nvl_choice",
        "_bubble",
        "bubble",
        "_yesno_prompt",
        "yesno_prompt",
        "ctc",
        "skip_indicator",
        "notify",
    }
)
BUILTIN_RENPY_SCREENS = ENGINE_COMMON_SCREENS  # Backward compatibility alias


RE_IMAGE_TAG = re.compile(r"\{image=([^}]+)\}")


@dataclass(frozen=True)
class ProjectContext:
    """Precomputed symbol and asset index for high-performance, deterministic rule execution."""

    project: RenPyProject
    catalog: AssetCatalog
    parsed_project: ParsedProject

    # Precomputed immutable indices
    labels_by_name: MappingProxyType[str, tuple[LabelSymbol, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    defined_labels: frozenset[str] = field(default_factory=frozenset)
    local_labels_by_scope: MappingProxyType[str, frozenset[str]] = field(
        default_factory=lambda: MappingProxyType({})
    )

    all_jumps: tuple[JumpReference, ...] = field(default_factory=tuple)
    all_calls: tuple[CallReference, ...] = field(default_factory=tuple)
    all_images: tuple[ImageDefinition, ...] = field(default_factory=tuple)
    all_audios: tuple[AudioReference, ...] = field(default_factory=tuple)
    audio_namespace_symbols: MappingProxyType[str, tuple[AssetInfo, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    _audio_cache: dict[AudioReference, AssetResolution] = field(
        default_factory=dict, repr=False, compare=False
    )
    all_variables: tuple[VariableDeclaration, ...] = field(default_factory=tuple)
    all_translations: tuple[TranslateBlock, ...] = field(default_factory=tuple)
    all_python_blocks: tuple[PythonBlock, ...] = field(default_factory=tuple)
    all_screens: tuple[ScreenDefinition, ...] = field(default_factory=tuple)
    defined_screens: frozenset[str] = field(default_factory=frozenset)
    screens_by_name: MappingProxyType[str, tuple[ScreenDefinition, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    screens_by_name_and_variant: MappingProxyType[
        tuple[str, Optional[str]], tuple[ScreenDefinition, ...]
    ] = field(default_factory=lambda: MappingProxyType({}))
    all_menus: tuple[MenuBlock, ...] = field(default_factory=tuple)
    all_dialogues: tuple[DialogueLine, ...] = field(default_factory=tuple)
    all_unreachables: tuple[UnreachableStatement, ...] = field(default_factory=tuple)

    defines_by_name: MappingProxyType[str, tuple[VariableDeclaration, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    defaults_by_name: MappingProxyType[str, tuple[VariableDeclaration, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    translations_by_lang: MappingProxyType[str, tuple[TranslateBlock, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )

    # Set of words/tokens found across script sources for unused asset analysis
    script_token_pool: frozenset[str] = field(default_factory=frozenset)
    # Audio channels explicitly registered via renpy.music.register_channel
    registered_audio_channels: frozenset[str] = field(default_factory=frozenset)
    all_init_statements: tuple[InitStatement, ...] = field(default_factory=tuple)
    custom_text_tags: frozenset[str] = field(default_factory=frozenset)
    custom_self_closing_text_tags: frozenset[str] = field(default_factory=frozenset)
    lifecycle_hook_labels: frozenset[str] = LIFECYCLE_HOOK_LABELS
    engine_common_screens: frozenset[str] = ENGINE_COMMON_SCREENS

    @property
    def _audio_resolutions(self) -> dict[AudioReference, AssetResolution]:
        """Backward-compatibility access to internal audio resolution cache."""
        return self._audio_cache

    @classmethod
    def build(
        cls,
        project: RenPyProject,
        catalog: AssetCatalog,
        parsed_project: ParsedProject,
    ) -> "ProjectContext":
        """Construct, index, and freeze all project symbols for deterministic rule execution."""
        # Temporary mutable builders
        raw_labels_by_name: dict[str, list[LabelSymbol]] = defaultdict(list)
        raw_defined_labels: set[str] = set()
        raw_local_labels: dict[str, set[str]] = defaultdict(set)

        raw_all_jumps: list[JumpReference] = []
        raw_all_calls: list[CallReference] = []
        raw_all_images: list[ImageDefinition] = []
        raw_all_audios: list[AudioReference] = []
        raw_all_variables: list[VariableDeclaration] = []
        raw_all_translations: list[TranslateBlock] = []
        raw_all_python_blocks: list[PythonBlock] = []
        raw_all_screens: list[ScreenDefinition] = []
        raw_defined_screens: set[str] = set()
        raw_screens_by_name: dict[str, list[ScreenDefinition]] = defaultdict(list)
        raw_screens_by_name_and_variant: dict[
            tuple[str, Optional[str]], list[ScreenDefinition]
        ] = defaultdict(list)
        raw_all_menus: list[MenuBlock] = []
        raw_all_dialogues: list[DialogueLine] = []
        raw_all_unreachables: list[UnreachableStatement] = []

        raw_defines_by_name: dict[str, list[VariableDeclaration]] = defaultdict(list)
        raw_defaults_by_name: dict[str, list[VariableDeclaration]] = defaultdict(list)
        raw_translations_by_lang: dict[str, list[TranslateBlock]] = defaultdict(list)

        raw_script_token_pool: set[str] = set()
        raw_registered_audio_channels: set[str] = set()
        raw_all_init_statements: list[InitStatement] = []
        raw_custom_text_tags: set[str] = set()
        raw_custom_self_closing_text_tags: set[str] = set()
        raw_audio_symbols: dict[str, list[AssetInfo]] = defaultdict(list)

        def add_token(token: str) -> None:
            clean = token.strip()
            if not clean:
                return
            raw_script_token_pool.add(clean)
            clean_lower = clean.lower()
            raw_script_token_pool.add(clean_lower)
            posix = clean.replace("\\", "/")
            raw_script_token_pool.add(posix)
            raw_script_token_pool.add(posix.lower())

            p = Path(posix)
            fname = p.name
            if fname:
                raw_script_token_pool.add(fname)
                raw_script_token_pool.add(fname.lower())
            stem = p.stem
            if stem:
                raw_script_token_pool.add(stem)
                raw_script_token_pool.add(stem.lower())
                raw_script_token_pool.add(stem.replace("_", " "))
                raw_script_token_pool.add(stem.replace("_", " ").lower())
                raw_script_token_pool.add(stem.replace(" ", "_"))
                raw_script_token_pool.add(stem.replace(" ", "_").lower())
            if "_" in clean:
                raw_script_token_pool.add(clean.replace("_", " "))
                raw_script_token_pool.add(clean.replace("_", " ").lower())
            if " " in clean:
                raw_script_token_pool.add(clean.replace(" ", "_"))
                raw_script_token_pool.add(clean.replace(" ", "_").lower())

        for file_result in parsed_project.files.values():
            # Index registered audio channels
            for ch in file_result.registered_channels:
                raw_registered_audio_channels.add(ch.lower())
                add_token(ch)

            # Index labels
            for lbl in file_result.labels:
                raw_labels_by_name[lbl.name].append(lbl)
                raw_defined_labels.add(lbl.name)

                if lbl.is_local and lbl.parent_label:
                    # e.g. parent="chapter", name=".choice" -> "chapter.choice"
                    full_local = f"{lbl.parent_label}{lbl.name}"
                    raw_defined_labels.add(full_local)
                    raw_local_labels[lbl.parent_label].add(lbl.name)
                elif not lbl.is_local:
                    raw_defined_labels.add(lbl.name)

            # Index screens
            for sc in file_result.screens:
                raw_all_screens.append(sc)
                raw_defined_screens.add(sc.name)
                raw_screens_by_name[sc.name].append(sc)
                raw_screens_by_name_and_variant[(sc.name, sc.variant)].append(sc)
                add_token(sc.name)

            # Collect references
            raw_all_jumps.extend(file_result.jumps)
            raw_all_calls.extend(file_result.calls)
            raw_all_images.extend(file_result.images)
            raw_all_audios.extend(file_result.audios)
            raw_all_variables.extend(file_result.variables)
            raw_all_translations.extend(file_result.translations)
            raw_all_python_blocks.extend(file_result.python_blocks)
            raw_all_menus.extend(file_result.menus)
            raw_all_dialogues.extend(file_result.dialogues)
            raw_all_unreachables.extend(file_result.unreachables)
            raw_all_init_statements.extend(file_result.init_statements)
            raw_custom_text_tags.update(file_result.custom_text_tags)
            raw_custom_self_closing_text_tags.update(file_result.custom_self_closing_text_tags)

            # Index define and default
            for var in file_result.variables:
                if var.kind == "define":
                    raw_defines_by_name[var.name].append(var)
                elif var.kind == "default":
                    raw_defaults_by_name[var.name].append(var)

            # Index translations
            for tr in file_result.translations:
                raw_translations_by_lang[tr.language].append(tr)

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

        # Index audio namespace symbols specifically from game/audio/
        for a in catalog.get_by_type(AssetType.AUDIO):
            norm_rel = a.relative_path.replace("\\", "/")
            if not (norm_rel.startswith("audio/") or norm_rel == "audio"):
                continue
            subpath = norm_rel[6:]  # remove "audio/" prefix
            p = Path(subpath)
            # Base stem (e.g. "click" from "audio/click.ogg")
            base_stem = p.stem.lower().replace(" ", "_").replace("-", "_")
            if base_stem.isidentifier():
                raw_audio_symbols[base_stem].append(a)

            # Subdirectory compound stem (e.g. "sfx_click" from "audio/sfx/click.ogg")
            parts = [part.lower().replace(" ", "_").replace("-", "_") for part in p.parts[:-1]]
            if parts:
                compound = f"{'_'.join(parts)}_{base_stem}"
                if compound.isidentifier():
                    raw_audio_symbols[compound].append(a)
                # Dot-separated hierarchy (e.g. "sfx.click")
                dot_path = f"{'.'.join(parts)}.{base_stem}"
                raw_audio_symbols[dot_path].append(a)

        # Deterministically sort candidate lists by relative_path
        for sym, candidates in raw_audio_symbols.items():
            candidates.sort(key=lambda x: x.relative_path)

        # Publish strictly immutable views and frozen containers
        ctx = cls(
            project=project,
            catalog=catalog,
            parsed_project=parsed_project,
            labels_by_name=MappingProxyType(
                {k: tuple(v) for k, v in raw_labels_by_name.items()}
            ),
            defined_labels=frozenset(raw_defined_labels),
            local_labels_by_scope=MappingProxyType(
                {k: frozenset(v) for k, v in raw_local_labels.items()}
            ),
            all_jumps=tuple(raw_all_jumps),
            all_calls=tuple(raw_all_calls),
            all_images=tuple(raw_all_images),
            all_audios=tuple(raw_all_audios),
            audio_namespace_symbols=MappingProxyType(
                {k: tuple(v) for k, v in raw_audio_symbols.items()}
            ),
            all_variables=tuple(raw_all_variables),
            all_translations=tuple(raw_all_translations),
            all_python_blocks=tuple(raw_all_python_blocks),
            all_screens=tuple(raw_all_screens),
            defined_screens=frozenset(raw_defined_screens),
            screens_by_name=MappingProxyType(
                {k: tuple(v) for k, v in raw_screens_by_name.items()}
            ),
            screens_by_name_and_variant=MappingProxyType(
                {k: tuple(v) for k, v in raw_screens_by_name_and_variant.items()}
            ),
            all_menus=tuple(raw_all_menus),
            all_dialogues=tuple(raw_all_dialogues),
            all_unreachables=tuple(raw_all_unreachables),
            defines_by_name=MappingProxyType(
                {k: tuple(v) for k, v in raw_defines_by_name.items()}
            ),
            defaults_by_name=MappingProxyType(
                {k: tuple(v) for k, v in raw_defaults_by_name.items()}
            ),
            translations_by_lang=MappingProxyType(
                {k: tuple(v) for k, v in raw_translations_by_lang.items()}
            ),
            script_token_pool=frozenset(raw_script_token_pool),
            registered_audio_channels=frozenset(raw_registered_audio_channels),
            all_init_statements=tuple(raw_all_init_statements),
            custom_text_tags=frozenset(raw_custom_text_tags),
            custom_self_closing_text_tags=frozenset(raw_custom_self_closing_text_tags),
        )

        # Precompute audio resolutions for all parsed script references
        for aud in ctx.all_audios:
            ctx.resolve_audio(aud)

        return ctx

    def has_label(self, label_name: str, scope: Optional[str] = None) -> bool:
        """Check whether a label is defined globally or within scope."""
        if label_name.startswith("."):
            if scope:
                full_name = f"{scope}{label_name}"
                return full_name in self.defined_labels
            return False
        return label_name in self.defined_labels

    def resolve_audio(self, audio_ref: AudioReference) -> AssetResolution:
        """Deterministically resolve an AudioReference according to Ren'Py semantics.

        Memoizes the result in _audio_resolutions so all rules share the exact same instance.
        """
        if audio_ref in self._audio_cache:
            return self._audio_cache[audio_ref]

        target = audio_ref.target
        clean_target = audio_ref.clean_target or target
        is_quoted = audio_ref.is_quoted
        clauses = audio_ref.clauses

        # 1. Unquoted identifiers (audio namespace or dynamic script variables)
        if not is_quoted:
            # Explicit audio store access: "audio.theme"
            if clean_target.startswith("audio."):
                lookup_sym = clean_target[6:]
                candidates = self.audio_namespace_symbols.get(lookup_sym, [])
                if len(candidates) == 1:
                    res = AssetResolution(
                        status=ResolutionStatus.AUDIO_NAMESPACE,
                        target=target,
                        clean_target=clean_target,
                        is_quoted=False,
                        asset=candidates[0],
                        candidates=tuple(candidates),
                        matched_path=candidates[0].relative_path,
                        clauses=clauses,
                    )
                elif len(candidates) > 1:
                    c_list = ", ".join(f"'{c.relative_path}'" for c in candidates)
                    res = AssetResolution(
                        status=ResolutionStatus.AMBIGUOUS,
                        target=target,
                        clean_target=clean_target,
                        is_quoted=False,
                        candidates=tuple(candidates),
                        clauses=clauses,
                        suggestion=f"Audio symbol '{lookup_sym}' matches multiple files: {c_list}",
                    )
                else:
                    res = AssetResolution(
                        status=ResolutionStatus.MISSING,
                        target=target,
                        clean_target=clean_target,
                        is_quoted=False,
                        clauses=clauses,
                        suggestion=f"Audio '{clean_target}' not found in 'game/audio/'.",
                    )
                self._audio_cache[audio_ref] = res
                return res

            # Bare identifier: check audio_namespace_symbols first
            candidates = self.audio_namespace_symbols.get(clean_target, [])
            if len(candidates) == 1:
                res = AssetResolution(
                    status=ResolutionStatus.AUDIO_NAMESPACE,
                    target=target,
                    clean_target=clean_target,
                    is_quoted=False,
                    asset=candidates[0],
                    candidates=tuple(candidates),
                    matched_path=candidates[0].relative_path,
                    clauses=clauses,
                )
            elif len(candidates) > 1:
                c_list = ", ".join(f"'{c.relative_path}'" for c in candidates)
                res = AssetResolution(
                    status=ResolutionStatus.AMBIGUOUS,
                    target=target,
                    clean_target=clean_target,
                    is_quoted=False,
                    candidates=tuple(candidates),
                    clauses=clauses,
                    suggestion=f"Audio symbol '{clean_target}' matches multiple files: {c_list}",
                )
            else:
                # Not in audio namespace: It is a dynamic variable or Python expression
                res = AssetResolution(
                    status=ResolutionStatus.DYNAMIC,
                    target=target,
                    clean_target=clean_target,
                    is_quoted=False,
                    clauses=clauses,
                )
            self._audio_cache[audio_ref] = res
            return res

        # 2. Quoted file paths (e.g. "music/song.ogg" or "theme.ogg")
        norm_path = clean_target.replace("\\", "/").strip("/")
        if not norm_path:
            res = AssetResolution(
                status=ResolutionStatus.MISSING,
                target=target,
                clean_target=clean_target,
                is_quoted=True,
                clauses=clauses,
                suggestion="Audio file path cannot be empty.",
            )
            self._audio_cache[audio_ref] = res
            return res

        # Ren'Py file path precedence:
        # Step 1: game/<norm_path>
        # Step 2: If not found and doesn't start with "audio/", game/audio/<norm_path>
        search_paths = [norm_path]
        if not norm_path.startswith("audio/"):
            search_paths.append(f"audio/{norm_path}")

        # Exact match check
        for p in search_paths:
            asset = self.catalog.find_exact(p)
            if asset and asset.asset_type in (AssetType.AUDIO, AssetType.VIDEO):
                res = AssetResolution(
                    status=ResolutionStatus.EXACT,
                    target=target,
                    clean_target=clean_target,
                    is_quoted=True,
                    asset=asset,
                    candidates=(asset,),
                    matched_path=asset.relative_path,
                    clauses=clauses,
                )
                self._audio_cache[audio_ref] = res
                return res

        # Case-insensitive check (Platform independent via catalog)
        folded_matches: list[AssetInfo] = []
        for p in search_paths:
            for m in self.catalog.find_case_insensitive(p):
                if m.asset_type in (AssetType.AUDIO, AssetType.VIDEO) and m not in folded_matches:
                    folded_matches.append(m)

        if len(folded_matches) == 1:
            res = AssetResolution(
                status=ResolutionStatus.CASE_MISMATCH,
                target=target,
                clean_target=clean_target,
                is_quoted=True,
                asset=folded_matches[0],
                candidates=tuple(folded_matches),
                matched_path=folded_matches[0].relative_path,
                clauses=clauses,
                suggestion=f"Update reference casing to match '{folded_matches[0].relative_path}'.",
            )
            self._audio_cache[audio_ref] = res
            return res
        elif len(folded_matches) > 1:
            folded_matches.sort(key=lambda x: x.relative_path)
            c_list = ", ".join(f"'{c.relative_path}'" for c in folded_matches)
            res = AssetResolution(
                status=ResolutionStatus.AMBIGUOUS,
                target=target,
                clean_target=clean_target,
                is_quoted=True,
                candidates=tuple(folded_matches),
                clauses=clauses,
                suggestion=f"Case-insensitive match is ambiguous across: {c_list}",
            )
            self._audio_cache[audio_ref] = res
            return res

        # Missing: Build heuristic diagnostic suggestions without giving false validity!
        p_stem = Path(norm_path).stem.lower()
        heuristic_candidates: list[AssetInfo] = []
        for a in self.catalog.get_by_type(AssetType.AUDIO):
            if Path(a.filename).stem.lower() == p_stem:
                heuristic_candidates.append(a)

        sug: Optional[str] = None
        if heuristic_candidates:
            heuristic_candidates.sort(key=lambda x: x.relative_path)
            c_paths = ", ".join(f"'{c.relative_path}'" for c in heuristic_candidates[:3])
            sug = f"Did you mean {c_paths}?"
        else:
            sug = f"Verify path or place '{clean_target}' in 'game/audio/'."

        res = AssetResolution(
            status=ResolutionStatus.MISSING,
            target=target,
            clean_target=clean_target,
            is_quoted=True,
            clauses=clauses,
            suggestion=sug,
        )
        self._audio_cache[audio_ref] = res
        return res

    def resolve_audio_asset(self, audio_target: str) -> Optional[AssetInfo]:
        """Backward-compatibility wrapper for legacy callers."""
        dummy_ref = AudioReference(
            channel="music",
            target=audio_target,
            location=Location(file_path="<legacy>"),
        )
        res = self.resolve_audio(dummy_ref)
        if res.status in (ResolutionStatus.EXACT, ResolutionStatus.AUDIO_NAMESPACE):
            return res.asset
        return None

