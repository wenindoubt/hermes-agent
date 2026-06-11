import logging

from gateway.reaction_feedback import (
    ReactionFeedbackEntry,
    parse_reaction_feedback,
    build_reaction_feedback_text,
)


def test_parse_dict_entry_with_label():
    out = parse_reaction_feedback(
        {"white_check_mark": {"label": "accepted/satisfied", "instruction": "Record positive feedback."}}
    )
    assert out == {
        "white_check_mark": ReactionFeedbackEntry(
            instruction="Record positive feedback.", label="accepted/satisfied"
        )
    }


def test_parse_bare_string_shorthand_defaults_label_empty():
    out = parse_reaction_feedback({"repeat": "Redo it."})
    assert out["repeat"] == ReactionFeedbackEntry(instruction="Redo it.", label="")


def test_parse_strips_surrounding_colons_on_key():
    out = parse_reaction_feedback({":repeat:": "Redo it."})
    assert "repeat" in out and ":repeat:" not in out


def test_parse_skips_entry_missing_instruction(caplog):
    with caplog.at_level(logging.WARNING, logger="gateway.reaction_feedback"):
        out = parse_reaction_feedback({"x": {"label": "negative/refine"}})
    assert out == {}
    assert "missing/empty 'instruction'" in caplog.text


def test_parse_skips_non_string_non_dict_value(caplog):
    with caplog.at_level(logging.WARNING, logger="gateway.reaction_feedback"):
        out = parse_reaction_feedback({"white_check_mark": 123})
    assert out == {}
    assert "expected string or mapping" in caplog.text


def test_parse_none_or_non_dict_returns_empty(caplog):
    assert parse_reaction_feedback(None) == {}
    with caplog.at_level(logging.WARNING, logger="gateway.reaction_feedback"):
        assert parse_reaction_feedback(["nope"]) == {}
    assert "expected a mapping" in caplog.text


def test_build_uses_label_when_present():
    entry = ReactionFeedbackEntry(instruction="Do the thing.", label="accepted/satisfied")
    text = build_reaction_feedback_text(
        entry, emoji="white_check_mark", message_ts="1.2", reacted_text="Hi"
    )
    assert "[Slack reaction feedback workflow]" in text
    assert "Reaction: :white_check_mark: (accepted/satisfied)" in text
    assert "Reacted message timestamp: 1.2" in text
    assert "Workflow instruction:\nDo the thing." in text
    assert "Reacted Hermes response:\nHi" in text
    assert "Prior thread context:" not in text


def test_build_falls_back_to_emoji_when_no_label_and_includes_thread_context():
    entry = ReactionFeedbackEntry(instruction="Do the thing.")
    text = build_reaction_feedback_text(
        entry, emoji="repeat", message_ts="1.2", reacted_text="", prior_thread_context="CTX"
    )
    assert "Reaction: :repeat: (repeat)" in text
    assert "Reacted Hermes response:\n[Unable to fetch reacted message text]" in text
    assert "Prior thread context:\nCTX" in text
