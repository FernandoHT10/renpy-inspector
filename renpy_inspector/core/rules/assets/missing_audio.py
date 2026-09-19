"""Rule detecting audio playback statements referencing nonexistent files."""

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.resolution import ResolutionStatus
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
            # Skip dynamic string interpolation patterns (e.g. "[current_track]")
            clean = audio.clean_target
            if not clean or ("[" in clean and "]" in clean):
                continue

            res = context.resolve_audio(audio)

            # Valid references (exact disk file or canonical audio namespace symbol)
            if res.status in (
                ResolutionStatus.EXACT,
                ResolutionStatus.AUDIO_NAMESPACE,
                ResolutionStatus.CASE_MISMATCH,
                ResolutionStatus.DYNAMIC,
            ):
                continue

            if res.status == ResolutionStatus.AMBIGUOUS:
                msg = (
                    f"Audio reference '{clean}' (channel: {audio.channel}) "
                    "is ambiguous and matches multiple files on disk."
                )
                issues.append(
                    self.create_issue(
                        message=msg,
                        location=audio.location,
                        suggestion=res.suggestion or "Disambiguate reference path.",
                        severity=Severity.WARNING,
                        metadata={
                            "target": clean,
                            "raw_target": audio.target,
                            "channel": audio.channel,
                            "action": audio.action,
                            "is_quoted": audio.is_quoted,
                        },
                    )
                )
            elif res.status == ResolutionStatus.MISSING:
                msg = (
                    f"Audio file '{clean}' (channel: {audio.channel}) "
                    "was not found in 'game/' or 'game/audio/'."
                )
                sug = res.suggestion or f"Verify path or place '{clean}' in 'game/audio/'."
                meta = {
                    "target": clean,
                    "raw_target": audio.target,
                    "channel": audio.channel,
                    "action": audio.action,
                    "is_quoted": audio.is_quoted,
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
