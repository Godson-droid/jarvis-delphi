"""Tests for the Agent Arena submission validator.

Run from the toolkit directory:
    python -m pytest tests/
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


def test_market_id_at_the_floor_fails():
    failures = failures_for(make_submission(market_id=1000))
    assert any("not above 1000" in failure for failure in failures)


def test_market_id_just_above_the_floor_passes():
    assert failures_for(make_submission(market_id=1001)) == []


def test_market_id_must_be_an_integer():
    failures = failures_for(make_submission(market_id="1234"))
    assert any("must be an integer" in failure for failure in failures)


def test_outcome_must_be_yes_or_no():
    failures = failures_for(make_submission(outcome="Maybe"))
    assert any("outcome must be one of" in failure for failure in failures)


def test_confidence_above_one_fails():
    failures = failures_for(make_submission(confidence=1.5))
    assert any("outside the allowed range" in failure for failure in failures)


def test_confidence_must_be_a_number():
    failures = failures_for(make_submission(confidence="high"))
    assert any("confidence must be a number" in failure for failure in failures)


def test_confidence_missing_fails():
    failures = failures_for(make_submission(confidence=None))
    assert any("confidence must be a number" in failure for failure in failures)


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


def state_with(market_id, outcome, when):
    state = SubmissionState()
    state.record(market_id, outcome, when)
    return state


def test_second_submission_on_same_market_within_the_hour_fails():
    state = state_with(1234, "Yes", NOW - timedelta(minutes=30))
    failures = failures_for(make_submission(), state=state)
    assert any("one submission per market per hour" in f for f in failures)


def test_submission_on_same_market_after_the_hour_passes():
    state = state_with(1234, "Yes", NOW - timedelta(minutes=61))
    assert failures_for(make_submission(), state=state) == []


def test_recent_submission_on_a_different_market_does_not_block():
    state = state_with(2222, "Yes", NOW - timedelta(minutes=5))
    assert failures_for(make_submission(), state=state) == []


def test_both_sides_of_one_market_fails():
    state = state_with(1234, "Yes", NOW - timedelta(hours=3))
    failures = failures_for(make_submission(outcome="No"), state=state)
    assert any("both sides" in failure for failure in failures)


def test_same_side_again_after_the_hour_passes():
    state = state_with(1234, "Yes", NOW - timedelta(hours=3))
    assert failures_for(make_submission(outcome="Yes"), state=state) == []


def test_daily_cap_blocks_the_fifty_first_submission():
    state = SubmissionState()
    for index in range(50):
        state.record(2000 + index, "Yes", NOW - timedelta(hours=2))
    failures = failures_for(make_submission(), state=state)
    assert any("daily paid submission cap" in f for f in failures)


def test_daily_cap_allows_the_fiftieth_submission():
    state = SubmissionState()
    for index in range(49):
        state.record(2000 + index, "Yes", NOW - timedelta(hours=2))
    assert failures_for(make_submission(), state=state) == []


def test_yesterdays_submissions_do_not_count_toward_today():
    state = SubmissionState()
    for index in range(50):
        state.record(2000 + index, "Yes", NOW - timedelta(days=1, hours=2))
    assert failures_for(make_submission(), state=state) == []


# --- sender stub ---------------------------------------------------


def test_sender_is_a_stub_until_the_guide_publishes():
    with pytest.raises(NotImplementedError):
        send_submission(make_submission())


# --- CLI -----------------------------------------------------------


def _run_cli(tmp_path, payload):
    target = tmp_path / "submission.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    cli = __file__.replace("tests/test_submission.py", "cli.py")
    return subprocess.run(
        [
            sys.executable,
            cli,
            str(target),
            "--at",
            "2026-11-25T17:00:00+01:00",
        ],
        capture_output=True,
        text=True,
    )


def test_cli_passes_a_valid_submission(tmp_path):
    result = _run_cli(
        tmp_path,
        {
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
        },
    )
    assert result.returncode == 0
    assert result.stdout.startswith("PASS")


def test_cli_reports_specific_failures(tmp_path):
    result = _run_cli(
        tmp_path,
        {"market_id": 12, "outcome": "Yes", "evidence": [], "confidence": 2},
    )
    assert result.returncode == 1
    assert result.stdout.startswith("FAIL")
    assert "not above 1000" in result.stdout
    assert "at least 1 evidence item" in result.stdout
