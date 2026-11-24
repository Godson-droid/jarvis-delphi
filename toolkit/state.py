"""Local record of submissions already sent, used by the validator
to enforce the cap of 3 submissions per agent per market and the
rule that this agent never evidences both sides of the same market,
and by the CLI to report progress toward the qualification floor
(at least 10 judged submissions across at least 3 markets).

The state file is plain JSON:

    {"submissions": [
        {"market_id": 1234, "outcome": "Yes",
         "submitted_at": "2026-11-25T17:05:00+00:00",
         "judged": false}
    ]}

The judged flag defaults to false (unjudged) and is set once the
competition records a judgement on that submission. Older state
files without the flag read as unjudged.

Nothing here talks to the network. The sending layer records a
submission only after Delphi accepts it.
"""

from __future__ import annotations

import json
import os

try:
    from . import rules
except ImportError:  # running as loose scripts inside the toolkit dir
    import rules


class SubmissionState:
    def __init__(self, records=None):
        self.records = list(records or [])

    @classmethod
    def load(cls, path):
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return cls(data.get("submissions", []))

    def save(self, path):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"submissions": self.records}, handle, indent=2)

    def record(self, market_id, outcome, submitted_at, judged=False):
        """Append one accepted submission. submitted_at is a datetime.
        judged records whether the competition has judged it yet."""
        self.records.append(
            {
                "market_id": market_id,
                "outcome": outcome,
                "submitted_at": submitted_at.isoformat(),
                "judged": bool(judged),
            }
        )

    def submission_count_for_market(self, market_id):
        """Total submissions recorded on one market, across all time.
        The per market cap of 3 is a whole competition cap, so no
        time window applies."""
        return sum(
            1 for record in self.records if record.get("market_id") == market_id
        )

    def recorded_outcome(self, market_id):
        """The outcome this agent has already evidenced on a market,
        or None. Both sides of one market cancel each other out, so a
        second side is never allowed."""
        for record in self.records:
            if record.get("market_id") == market_id:
                return record.get("outcome")
        return None

    def qualification_progress(self):
        """Progress toward the qualification floor, from the records
        flagged as judged: how many judged submissions, across how
        many distinct markets, against the rules constants."""
        judged = [record for record in self.records if record.get("judged")]
        markets = {record.get("market_id") for record in judged}
        return {
            "judged_submissions": len(judged),
            "judged_markets": len(markets),
            "min_judged_submissions": rules.QUALIFICATION_MIN_JUDGED_SUBMISSIONS,
            "min_markets": rules.QUALIFICATION_MIN_MARKETS,
            "qualified": len(judged) >= rules.QUALIFICATION_MIN_JUDGED_SUBMISSIONS
            and len(markets) >= rules.QUALIFICATION_MIN_MARKETS,
        }
