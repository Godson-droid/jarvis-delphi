"""Local record of submissions already sent, used by the validator
to enforce the per market hourly limit, the daily paid cap and the
rule that this agent never evidences both sides of the same market.

The state file is plain JSON:

    {"submissions": [
        {"market_id": 1234, "outcome": "Yes",
         "submitted_at": "2026-11-25T17:05:00+00:00"}
    ]}

Nothing here talks to the network. The sending layer records a
submission only after Delphi accepts it.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

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

    def record(self, market_id, outcome, submitted_at):
        """Append one accepted submission. submitted_at is a datetime."""
        self.records.append(
            {
                "market_id": market_id,
                "outcome": outcome,
                "submitted_at": submitted_at.isoformat(),
            }
        )

    def _times_for_market(self, market_id):
        times = []
        for record in self.records:
            if record.get("market_id") == market_id:
                try:
                    times.append(datetime.fromisoformat(record["submitted_at"]))
                except (KeyError, ValueError):
                    continue
        return sorted(times)

    def seconds_since_last_submission(self, market_id, now):
        """Seconds between now and the newest recorded submission on
        this market, or None if the market has none."""
        times = self._times_for_market(market_id)
        if not times:
            return None
        return (now - times[-1]).total_seconds()

    def recorded_outcome(self, market_id):
        """The outcome this agent has already evidenced on a market,
        or None. Both sides of one market cancel each other out, so a
        second side is never allowed."""
        for record in self.records:
            if record.get("market_id") == market_id:
                return record.get("outcome")
        return None

    def paid_submissions_on(self, day, timezone_name=None):
        """Count of recorded submissions whose local calendar date
        (in the rules timezone) equals the given date."""
        tz = ZoneInfo(timezone_name or rules.DAILY_COUNT_TIMEZONE)
        count = 0
        for record in self.records:
            try:
                moment = datetime.fromisoformat(record["submitted_at"])
            except (KeyError, ValueError):
                continue
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=tz)
            if moment.astimezone(tz).date() == day:
                count += 1
        return count
