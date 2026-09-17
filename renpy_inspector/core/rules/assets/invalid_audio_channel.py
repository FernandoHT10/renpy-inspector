"""Rule detecting playback on unrecognized or misspelled audio channels."""

from typing import List

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.rules.base import Rule

STANDARD_CHANNELS = frozenset({"music", "sound", "voice", "audio", "movie"})


class InvalidAudioChannelRule(Rule):
    """Detects audio statements targeting non-standard or misspelled audio channels."""

    rule_id = "RPY-AUDIO-002"
    title = "Invalid Audio Channel"
    category = Category.ASSETS
    default_severity = Severity.WARNING
    description = (
        "Checks that audio statements use recognized standard or registered channels."
    )

    def analyze(self, context: ProjectContext) -> List[Issue]:
        issues: List[Issue] = []

        for audio in context.all_audios:
            ch = audio.channel.strip().lower()
            if ch in STANDARD_CHANNELS:
                continue

            # If the custom channel was registered via renpy.music.register_channel
            if ch in context.registered_audio_channels:
                continue

            # If the custom channel is mentioned in Python scripts or variable token pool
            if ch in context.script_token_pool:
                continue

            issues.append(
                Issue.create(
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    category=self.category,
                    title=f"Unrecognized Audio Channel '{ch}'",
                    message=(
                        f"The audio statement targets channel '{ch}', which is not a standard "
                        "Ren'Py channel (music, sound, voice, audio) or known registered channel."
                    ),
                    location=audio.location,
                    suggestion=(
                        f"Check for typos (e.g., 'music', 'sound', 'voice') or register '{ch}' "
                        "using 'renpy.music.register_channel()'."
                    ),
                )
            )

        return issues
