"""Rule detecting audio playback statements referencing nonexistent files."""

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.symbols import ReferenceKind
from renpy_inspector.core.rules.base import BaseRule


class MissingAudioRule(BaseRule):
    """Detects missing audio assets while safely handling dynamic variables."""

    rule_id = "RPY-AUDIO-001"
    title = "Missing Audio File"
    category = Category.AUDIO
    default_severity = Severity.ERROR
    description = "Checks that static audio paths referenced in play/queue statements exist."

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        for audio in context.all_audios:
            # Skip dynamic audio variables or audio namespace references
            if audio.kind == ReferenceKind.DYNAMIC:
                continue

            target = audio.target.strip("\"'").replace("\\", "/")
            if not target or ("[" in target and "]" in target):
                continue

            asset = context.resolve_audio_asset(target)
            if asset is None:
                msg = (
                    f"Audio file '{target}' (channel: {audio.channel}) "
                    "was not found in 'game/' or 'game/audio/'."
                )
                sug = f"Verify path or place '{target}' in 'game/audio/'."
                meta = {
                    "target": target,
                    "channel": audio.channel,
                    "action": audio.action,
                }
                issues.append(
                    self.create_issue(
                        message=msg,
                        location=audio.location,
                        suggestion=sug,
                        metadata=meta,
                    )
                )

        return issues
