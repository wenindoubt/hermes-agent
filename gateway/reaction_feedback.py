"""Platform-agnostic reaction-feedback configuration.

A user reacts to a bot message with an emoji; that emoji maps (via user config)
to an instruction string injected back to the agent as a feedback turn.

The map is keyed by the *platform-native* reaction identifier (for Slack, the
bare ``reaction_added`` shortcode such as ``thumbsup``). When promoted to other
platforms, each adapter normalizes its inbound reaction into this key space
before lookup (Slack strips the ``::skin-tone-N`` suffix and surrounding colons;
unicode platforms pass the glyph through). Keep this module free of
platform-specific imports.
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

    Tolerant by design — never raises, so malformed config can't stop the
    gateway from starting (mirrors the ``_coerce_*`` helpers in gateway/config.py):

    - ``None`` / non-dict ``raw`` -> ``{}`` (feature disabled).
    - Each value may be a ``{"instruction": ..., "label": ...}`` mapping or a
      bare instruction string (label then defaults to the emoji key at render).
    - Surrounding colons on the key are stripped (``:repeat:`` -> ``repeat``).
    - Entries with an empty/missing instruction are logged and skipped.
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

    The header literal is currently Slack-specific; parameterize it when this
    module is promoted to other platforms.
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
