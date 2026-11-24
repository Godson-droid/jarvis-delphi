"""Tests for the Agent Arena submission validator.

Run from the toolkit directory:
    python -m pytest tests/

The rules under test are the settled rules from the two first hand
live reads of the competition page on 2026-11-24 (see rules.py):
at most 3 submissions per agent per market, at most 3 files per
submission, one side per market, dated sourced evidence. There is
no market ID floor, no per market hourly limit and no daily cap.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from sender import send_submission
from state import SubmissionState
from submission import EvidenceItem, Submission, validate_submission

WAT = ZoneInfo("Africa/Lagos")
NOW = datetime(2026, 11, 25, 17, 0, 0, tzinfo=WAT)


def make_item(**overrides):
    fields = {
        "source_url": "https://example.org/report",
        "summary": "The report confirms the event happened.",
        "quote": "We can confirm the event happened on Monday.",
        "published_date": "2026-11-24",
    }
    fields.update(overrides)
    return EvidenceItem(**fields)


def make_submission(**overrides):
    fields = {
        "market_id": 1234,
        "outcome": "Yes",
        "evidence": [make_item()],
        "confidence": 0.7,
    }
    fields.update(overrides)
    return Submission(**fields)


def failures_for(submission, state=None, now=NOW):
    return validate_submission(submission, state=state, now=now)


# --- format rules -------------------------------------------------


def test_valid_submission_passes():
    assert failures_for(make_submission()) == []


def test_low_market_id_passes():
    # The settled rules carry no market ID floor.
    assert failures_for(make_submission(market_id=12)) == []
    assert failures_for(make_submission(market_id=7)) == []


def test_market_id_must_be_an_integer():
    failures = failures_for(make_submission(market_id="1234"))
    assert any("must be an integer" in failure for failure in failures)


def test_outcome_must_be_yes_or_no():
    failures = failures_for(make_submission(outcome="Maybe"))
    assert any("outcome must be one of" in failure for failure in failures)


def test_confidence_is_optional():
    # The current page does not mention confidence; the validator
    # must not require it.
    assert failures_for(make_submission(confidence=None)) == []


def test_confidence_above_one_fails_when_supplied():
    failures = failures_for(make_submission(confidence=1.5))
    assert any("outside the allowed range" in failure for failure in failures)


def test_confidence_must_be_a_number_when_supplied():
    failures = failures_for(make_submission(confidence="high"))
    assert any("confidence must be a number" in failure for failure in failures)


def test_three_attachments_pass():
    submission = make_submission(attachments=["a.png", "b.csv", "c.txt"])
    assert failures_for(submission) == []


def test_four_attachments_fail():
    submission = make_submission(attachments=["a.png", "b.csv", "c.txt", "d.png"])
    failures = failures_for(submission)
    assert any("at most 3 files" in failure for failure in failures)


def test_at_least_one_evidence_item_required():
    failures = failures_for(make_submission(evidence=[]))
    assert any("at least 1 evidence item" in failure for failure in failures)


def test_item_missing_source_url_fails():
    failures = failures_for(make_submission(evidence=[make_item(source_url="")]))
    assert any("no usable source_url" in failure for failure in failures)


def test_item_with_non_web_source_url_fails():
    failures = failures_for(
        make_submission(evidence=[make_item(source_url="a book on my shelf")])
    )
    assert any("no usable source_url" in failure for failure in failures)


def test_item_missing_summary_fails():
    failures = failures_for(make_submission(evidence=[make_item(summary=" ")]))
    assert any("missing a summary" in failure for failure in failures)


def test_item_missing_quote_fails():
    failures = failures_for(make_submission(evidence=[make_item(quote="")]))
    assert any("missing a verbatim quote" in failure for failure in failures)


def test_item_missing_published_date_fails():
    failures = failures_for(
        make_submission(evidence=[make_item(published_date="")])
    )
    assert any("missing a valid published_date" in failure for failure in failures)


def test_item_with_unparseable_published_date_fails():
    failures = failures_for(
        make_submission(evidence=[make_item(published_date="last Tuesday")])
    )
    assert any("missing a valid published_date" in failure for failure in failures)


def test_item_with_future_published_date_fails():
    failures = failures_for(
        make_submission(evidence=[make_item(published_date="2026-12-01")])
    )
    assert any("in the future" in failure for failure in failures)


def test_item_with_datetime_published_date_passes():
    item = make_item(published_date="2026-11-24T09:30:00Z")
    assert failures_for(make_submission(evidence=[item])) == []


# --- state dependent rules ----------------------------------------


def state_with(market_id, outcome, when, judged=False):
    state = SubmissionState()
    state.record(market_id, outcome, when, judged=judged)
    return state


def test_second_submission_to_a_different_market_in_the_same_hour_passes():
    # There is no hourly limit in the settled rules.
    state = state_with(2222, "Yes", NOW - timedelta(minutes=5))
    assert failures_for(make_submission(), state=state) == []


def test_repeat_submission_on_same_market_minutes_later_passes():
    # No hourly limit on the same market either, while under the cap.
    state = state_with(1234, "Yes", NOW - timedelta(minutes=5))
    assert failures_for(make_submission(), state=state) == []


def test_third_submission_on_a_market_passes():
    state = SubmissionState()
    state.record(1234, "Yes", NOW - timedelta(days=2))
    state.record(1234, "Yes", NOW - timedelta(days=1))
    assert failures_for(make_submission(), state=state) == []


def test_fourth_submission_on_a_market_fails():
    state = SubmissionState()
    state.record(1234, "Yes", NOW - timedelta(days=3))
    state.record(1234, "Yes", NOW - timedelta(days=2))
    state.record(1234, "Yes", NOW - timedelta(days=1))
    failures = failures_for(make_submission(), state=state)
    assert any("at most 3 submissions per agent per market" in f for f in failures)


def test_per_market_cap_counts_across_all_time():
    # Submissions spread over weeks still count toward the cap of 3.
    state = SubmissionState()
    state.record(1234, "Yes", NOW - timedelta(days=30))
    state.record(1234, "Yes", NOW - timedelta(days=20))
    state.record(1234, "Yes", NOW - timedelta(days=10))
    failures = failures_for(make_submission(), state=state)
    assert any("at most 3 submissions per agent per market" in f for f in failures)


def test_cap_on_one_market_does_not_block_another():
    state = SubmissionState()
    for days in (3, 2, 1):
        state.record(1234, "Yes", NOW - timedelta(days=days))
    assert failures_for(make_submission(market_id=2222), state=state) == []


def test_both_sides_of_one_market_fails():
    state = state_with(1234, "Yes", NOW - timedelta(hours=3))
    failures = failures_for(make_submission(outcome="No"), state=state)
    assert any("both sides" in failure for failure in failures)


def test_same_side_again_passes():
    state = state_with(1234, "Yes", NOW - timedelta(hours=3))
    assert failures_for(make_submission(outcome="Yes"), state=state) == []


def test_many_submissions_in_one_day_pass():
    # There is no daily cap in the settled rules.
    state = SubmissionState()
    for index in range(60):
        state.record(2000 + index, "Yes", NOW - timedelta(hours=2))
    assert failures_for(make_submission(), state=state) == []


# --- qualification progress ----------------------------------------


def test_qualification_progress_counts_only_judged():
    state = SubmissionState()
    state.record(100, "Yes", NOW, judged=True)
    state.record(100, "Yes", NOW, judged=True)
    state.record(200, "No", NOW, judged=True)
    state.record(300, "Yes", NOW)  # unjudged by default
    progress = state.qualification_progress()
    assert progress["judged_submissions"] == 3
    assert progress["judged_markets"] == 2
    assert progress["qualified"] is False


def test_qualification_progress_met_at_the_floor():
    state = SubmissionState()
    for index in range(10):
        state.record(100 + (index % 3), "Yes", NOW, judged=True)
    progress = state.qualification_progress()
    assert progress["judged_submissions"] == 10
    assert progress["judged_markets"] == 3
    assert progress["qualified"] is True


def test_records_default_to_unjudged():
    state = SubmissionState()
    state.record(100, "Yes", NOW)
    assert state.records[0]["judged"] is False


# --- sender stub ---------------------------------------------------


def test_sender_is_a_stub_until_the_guide_publishes():
    with pytest.raises(NotImplementedError):
        send_submission(make_submission())


# --- CLI -----------------------------------------------------------


def _run_cli(tmp_path, payload, state_records=None):
    target = tmp_path / "submission.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    cli = __file__.replace("tests/test_submission.py", "cli.py")
    command = [
        sys.executable,
        cli,
        str(target),
        "--at",
        "2026-11-25T17:00:00+01:00",
    ]
    if state_records is not None:
        state_path = tmp_path / "state.json"
        state_path.write_text(
            json.dumps({"submissions": state_records}), encoding="utf-8"
        )
        command += ["--state", str(state_path)]
    return subprocess.run(command, capture_output=True, text=True)


def _valid_payload(**overrides):
    payload = {
        "market_id": 1234,
        "outcome": "Yes",
        "evidence": [
            {
                "source_url": "https://example.org/report",
                "summary": "The report confirms the event happened.",
                "quote": "We can confirm the event happened on Monday.",
                "published_date": "2026-11-24",
            }
        ],
        "confidence": 0.7,
    }
    payload.update(overrides)
    return payload


def test_cli_passes_a_valid_submission(tmp_path):
    result = _run_cli(tmp_path, _valid_payload())
    assert result.returncode == 0
    assert result.stdout.startswith("PASS")


def test_cli_passes_a_low_market_id_without_confidence(tmp_path):
    payload = _valid_payload(market_id=12)
    del payload["confidence"]
    result = _run_cli(tmp_path, payload)
    assert result.returncode == 0
    assert result.stdout.startswith("PASS")


def test_cli_reports_specific_failures(tmp_path):
    result = _run_cli(
        tmp_path,
        {"market_id": 12, "outcome": "Yes", "evidence": [], "confidence": 2},
    )
    assert result.returncode == 1
    assert result.stdout.startswith("FAIL")
    assert "at least 1 evidence item" in result.stdout
    assert "outside the allowed range" in result.stdout


def test_cli_reports_qualification_progress_from_state(tmp_path):
    records = [
        {
            "market_id": 100,
            "outcome": "Yes",
            "submitted_at": "2026-11-25T10:00:00+01:00",
            "judged": True,
        },
        {
            "market_id": 200,
            "outcome": "No",
            "submitted_at": "2026-11-25T11:00:00+01:00",
            "judged": True,
        },
        {
            "market_id": 300,
            "outcome": "Yes",
            "submitted_at": "2026-11-25T12:00:00+01:00",
            "judged": False,
        },
    ]
    result = _run_cli(tmp_path, _valid_payload(), state_records=records)
    assert result.returncode == 0
    assert "Qualification progress: 2 of 10 judged submissions" in result.stdout
    assert "across 2 of 3 markets" in result.stdout
