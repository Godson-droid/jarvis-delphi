"""Command line validator for Agent Arena evidence submissions.

Usage:
    python cli.py SUBMISSION.json [--state STATE.json] [--at ISO_TIME]

Reads a submission JSON file, validates it against the competition
rules in rules.py and, when a state file is given or the default
state file exists, against the record of submissions already sent.
Prints PASS and exits 0, or prints each failure and exits 1. When a
state file is in play it also prints progress toward the
qualification floor (at least 10 judged submissions across at
least 3 markets).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rules
from state import SubmissionState
from submission import Submission, validate_submission

DEFAULT_STATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "state.json"
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission_file", help="Path to a submission JSON file")
    parser.add_argument(
        "--state",
        default=None,
        help="Path to the submission state file "
        "(default: state.json beside this script, if it exists)",
    )
    parser.add_argument(
        "--at",
        default=None,
        help="Validate as if at this ISO datetime (for testing)",
    )
    args = parser.parse_args(argv)

    with open(args.submission_file, "r", encoding="utf-8") as handle:
        submission = Submission.from_dict(json.load(handle))

    state_path = args.state or DEFAULT_STATE_PATH
    state = SubmissionState.load(state_path) if os.path.exists(state_path) else None

    now = None
    if args.at:
        now = datetime.fromisoformat(args.at.replace("Z", "+00:00"))

    failures = validate_submission(submission, state=state, now=now)
    if failures:
        print("FAIL")
        for failure in failures:
            print(" - %s" % failure)
        result = 1
    else:
        print("PASS")
        result = 0

    if state is not None:
        progress = state.qualification_progress()
        line = (
            "Qualification progress: %d of %d judged submissions across "
            "%d of %d markets"
            % (
                progress["judged_submissions"],
                rules.QUALIFICATION_MIN_JUDGED_SUBMISSIONS,
                progress["judged_markets"],
                rules.QUALIFICATION_MIN_MARKETS,
            )
        )
        if progress["qualified"]:
            line += " (qualification floor met)"
        print(line)

    return result


if __name__ == "__main__":
    sys.exit(main())
