"""Evidence submission model and validator for the Agent Arena.

A submission, in the format recorded from the live competition page
on 2026-11-23, is:

    {
      "market_id": 1234,
      "outcome": "Yes",
      "evidence": [
        {
          "source_url": "https://example.org/article",
          "summary": "One or two plain sentences on what the source shows.",
          "quote": "A verbatim quote copied from the source.",
          "published_date": "2026-11-24"
        }
      ],
      "confidence": 0.7,
      "note": "Optional short note."
    }

The validator enforces the competition rules locally, before
anything is sent anywhere. Every limit comes from rules.py, the
single rules constants file. validate_submission returns a list of
human readable failures; an empty list means the submission passes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

try:
    from . import rules
    from .state import SubmissionState
except ImportError:  # running as loose scripts inside the toolkit dir
    import rules
    from state import SubmissionState


@dataclass
class EvidenceItem:
    source_url: str = ""
    summary: str = ""
    quote: str = ""
    published_date: str = ""

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            source_url=data.get("source_url", ""),
            summary=data.get("summary", ""),
            quote=data.get("quote", ""),
            published_date=data.get("published_date", ""),
        )

    def to_dict(self):
        return {
            "source_url": self.source_url,
            "summary": self.summary,
            "quote": self.quote,
            "published_date": self.published_date,
        }


@dataclass
class Submission:
    market_id: object = None
    outcome: str = ""
    evidence: list = field(default_factory=list)
    confidence: object = None
    note: str = ""

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        items = [EvidenceItem.from_dict(item) for item in data.get("evidence", [])]
        return cls(
            market_id=data.get("market_id"),
            outcome=data.get("outcome", ""),
            evidence=items,
            confidence=data.get("confidence"),
            note=data.get("note", ""),
        )

    def to_dict(self):
        return {
            "market_id": self.market_id,
            "outcome": self.outcome,
            "evidence": [item.to_dict() for item in self.evidence],
            "confidence": self.confidence,
            "note": self.note,
        }


def _parse_published_date(value):
    """Return a date for an ISO date or datetime string, else None."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _is_real_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_submission(submission, state=None, now=None):
    """Validate one Submission. Returns a list of failure strings;
    an empty list means pass.

    state is an optional SubmissionState of already accepted
    submissions; when given, the hourly per market limit, the daily
    paid cap and the single side rule are enforced against it.
    now is an optional aware datetime for tests; defaults to the
    current time in the rules timezone.
    """
    failures = []
    if now is None:
        now = datetime.now(ZoneInfo(rules.DAILY_COUNT_TIMEZONE))
    today = now.date()

    # Market ID: an integer strictly above the recorded floor.
    if isinstance(submission.market_id, bool) or not isinstance(
        submission.market_id, int
    ):
        failures.append(
            "market_id must be an integer, got %r" % (submission.market_id,)
        )
    elif submission.market_id <= rules.MIN_MARKET_ID_EXCLUSIVE:
        failures.append(
            "market_id %d is not above %d; submissions are only allowed "
            "on markets with an ID over %d"
            % (
                submission.market_id,
                rules.MIN_MARKET_ID_EXCLUSIVE,
                rules.MIN_MARKET_ID_EXCLUSIVE,
            )
        )

    # Outcome: exactly one side of a Yes or No market.
    if submission.outcome not in rules.VALID_OUTCOMES:
        failures.append(
            "outcome must be one of %s, got %r"
            % (", ".join(rules.VALID_OUTCOMES), submission.outcome)
        )

    # Confidence: a score inside the recorded range.
    if not _is_real_number(submission.confidence):
        failures.append(
            "confidence must be a number, got %r" % (submission.confidence,)
        )
    elif not (rules.CONFIDENCE_MIN <= submission.confidence <= rules.CONFIDENCE_MAX):
        failures.append(
            "confidence %r is outside the allowed range %s to %s"
            % (submission.confidence, rules.CONFIDENCE_MIN, rules.CONFIDENCE_MAX)
        )

    # Evidence items: at least one, each fully sourced and dated.
    if len(submission.evidence) < rules.MIN_EVIDENCE_ITEMS:
        failures.append(
            "a submission needs at least %d evidence item(s)"
            % rules.MIN_EVIDENCE_ITEMS
        )
    for index, item in enumerate(submission.evidence):
        label = "evidence item %d" % (index + 1)
        parsed = urlparse(item.source_url or "")
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            failures.append(
                "%s has no usable source_url: %r" % (label, item.source_url)
            )
        if not (item.summary or "").strip():
            failures.append("%s is missing a summary" % label)
        if not (item.quote or "").strip():
            failures.append(
                "%s is missing a verbatim quote from the source" % label
            )
        published = _parse_published_date(item.published_date)
        if published is None:
            failures.append(
                "%s is missing a valid published_date (ISO date), got %r; "
                "real dated sources only" % (label, item.published_date)
            )
        elif published > today:
            failures.append(
                "%s has published_date %s, which is in the future; "
                "real dated sources only" % (label, published.isoformat())
            )

    # State dependent rules, checked only when a state is supplied and
    # the market ID is usable.
    if state is not None and isinstance(submission.market_id, int) and not isinstance(
        submission.market_id, bool
    ):
        elapsed = state.seconds_since_last_submission(submission.market_id, now)
        if elapsed is not None and elapsed < rules.MIN_SECONDS_BETWEEN_SUBMISSIONS_PER_MARKET:
            remaining = int(
                rules.MIN_SECONDS_BETWEEN_SUBMISSIONS_PER_MARKET - elapsed
            )
            failures.append(
                "market %d already received a submission %d seconds ago; "
                "at most one submission per market per hour, wait %d more "
                "seconds" % (submission.market_id, int(elapsed), remaining)
            )
        earlier_outcome = state.recorded_outcome(submission.market_id)
        if earlier_outcome is not None and earlier_outcome != submission.outcome:
            failures.append(
                "market %d was already evidenced for %s; this agent never "
                "evidences both sides of one market (the two sides cancel "
                "out)" % (submission.market_id, earlier_outcome)
            )
        sent_today = state.paid_submissions_on(today)
        if sent_today >= rules.MAX_PAID_SUBMISSIONS_PER_DAY:
            failures.append(
                "daily paid submission cap reached: %d already sent today "
                "(limit %d)" % (sent_today, rules.MAX_PAID_SUBMISSIONS_PER_DAY)
            )

    return failures


def utcnow():
    return datetime.now(timezone.utc)
