"""Rule detecting missing translation blocks across supported project languages."""

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.location import Location
from renpy_inspector.core.rules.base import BaseRule


class MissingTranslationRule(BaseRule):
    """Detects dialogue translation blocks existing in some languages but missing in others."""

    rule_id = "RPY-TL-001"
    title = "Missing Translation Block"
    category = Category.TRANSLATION
    default_severity = Severity.WARNING
    description = (
        "Checks that translated dialogue blocks are consistent across all target languages."
    )

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        # Ignore base language None and placeholder translation templates
        template_languages = {"none", "yourlanguage", "template", "example", "sample"}
        real_languages = [
            lang for lang in context.translations_by_lang.keys()
            if lang.lower() not in template_languages
        ]

        if len(real_languages) < 2:
            return issues

        # Collect all dialogue identifiers (excluding 'strings' and 'python')
        all_dialogue_ids: set[str] = set()
        for lang in real_languages:
            for tr in context.translations_by_lang[lang]:
                ident = tr.identifier
                if ident not in ("strings", "python", "style") and not ident.startswith("style "):
                    all_dialogue_ids.add(ident)

        max_per_lang = 25

        for lang in sorted(real_languages):
            lang_ids = {
                tr.identifier for tr in context.translations_by_lang[lang]
            }
            missing_ids = sorted(all_dialogue_ids - lang_ids)
            if not missing_ids:
                continue

            # Emit detailed issues up to max_per_lang
            for missing_id in missing_ids[:max_per_lang]:
                msg = f"Translation block '{missing_id}' is missing in language '{lang}'."
                sug = (
                    f"Generate updated translations with Ren'Py Launcher or add "
                    f"'translate {lang} {missing_id}:'."
                )
                issues.append(
                    self.create_issue(
                        message=msg,
                        location=Location(file_path=f"game/tl/{lang}/script.rpy"),
                        suggestion=sug,
                        metadata={"language": lang, "missing_identifier": missing_id},
                    )
                )

            # If there are many missing blocks, emit a consolidated summary issue
            if len(missing_ids) > max_per_lang:
                msg = (
                    f"Language '{lang}' is missing {len(missing_ids)} translation blocks in total "
                    f"({max_per_lang} detailed above)."
                )
                sug = (
                    f"Run 'Generate Translations' in Ren'Py Launcher to create the "
                    f"{len(missing_ids) - max_per_lang} remaining translation stubs for '{lang}'."
                )
                issues.append(
                    self.create_issue(
                        message=msg,
                        location=Location(file_path=f"game/tl/{lang}/script.rpy"),
                        suggestion=sug,
                        metadata={"language": lang, "total_missing": len(missing_ids)},
                    )
                )

        return issues
