"""Platform-agnostic reaction-feedback config.

A user reacts to a bot message with an emoji; that emoji maps (via user config)
to an instruction injected back to the agent as a feedback turn.

Keys are the platform-native reaction id (Slack: the bare ``reaction_added``
shortcode like ``thumbsup``). Each adapter normalizes its reactions into that
key space before lookup. Keep this module free of platform-specific imports.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReactionFeedbackEntry:
    """One configured reaction: the instruction to inject + an optional label."""

    instruction: str
    label: str = ""


def parse_reaction_feedback(raw: Any) -> Dict[str, ReactionFeedbackEntry]:
    """Parse a ``reaction_feedback`` config block into ``emoji -> entry``.

    Tolerant by design — never raises, so bad config can't stop the gateway
    from starting (like the ``_coerce_*`` helpers in gateway/config.py):

    - non-dict ``raw`` -> ``{}`` (feature off).
    - each value is a ``{"instruction", "label"}`` mapping or a bare
      instruction string (label then defaults to the emoji at render).
    - surrounding colons on keys are stripped (``:repeat:`` -> ``repeat``).
    - entries missing an instruction are logged and skipped.
    """
    if not isinstance(raw, dict):
        if raw is not None:
            logger.warning(
                "Ignoring reaction_feedback config: expected a mapping, got %s",
                type(raw).__name__,
            )
        return {}

    parsed: Dict[str, ReactionFeedbackEntry] = {}
    for key, value in raw.items():
        emoji = str(key).strip().strip(":")
        if not emoji:
            logger.warning("Skipping reaction_feedback entry with empty emoji key")
            continue

        if isinstance(value, str):
            instruction, label = value.strip(), ""
        elif isinstance(value, dict):
            instruction = str(value.get("instruction") or "").strip()
            label = str(value.get("label") or "").strip()
        else:
            logger.warning(
                "Skipping reaction_feedback[%s]: expected string or mapping, got %s",
                emoji,
                type(value).__name__,
            )
            continue

        if not instruction:
            logger.warning(
                "Skipping reaction_feedback[%s]: missing/empty 'instruction'", emoji
            )
            continue

        parsed[emoji] = ReactionFeedbackEntry(instruction=instruction, label=label)

    return parsed


def build_reaction_feedback_text(
    entry: ReactionFeedbackEntry,
    *,
    emoji: str,
    message_ts: str,
    reacted_text: str,
    prior_thread_context: str = "",
) -> str:
    """Render the synthetic feedback-turn text for a reacted message.

    Header is Slack-specific for now; parameterize when promoted to other
    platforms.
    """
    label = entry.label or emoji
    parts = [
        "[Slack reaction feedback workflow]",
        f"Reaction: :{emoji}: ({label})",
        f"Reacted message timestamp: {message_ts}",
        "",
        "Workflow instruction:",
        entry.instruction,
        "",
        "Reacted Hermes response:",
        reacted_text or "[Unable to fetch reacted message text]",
    ]
    if prior_thread_context:
        parts.extend(["", "Prior thread context:", prior_thread_context])
    return "\n".join(parts)
