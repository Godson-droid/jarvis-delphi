"""Competition rules constants for the Agent Arena evidence toolkit.

=====================================================================
RULES CONSTANTS: SINGLE SOURCE OF TRUTH
Every rules dependent value in this toolkit lives in this file and
nowhere else. If a rule changes, edit it here and the validator, the
state tracker and the CLI all follow.

Source of these values: two first hand live reads of the DoraHacks
competition page for the Gensyn Agent Arena (delphi agent
competition) on 2026-11-24, one at 10:53 WAT and a signed in read at
11:17 WAT, which agree with each other. They supersede the earlier
2026-11-23 read this toolkit was first built to: the settled rules
below carry no market ID floor, no per market hourly limit and no
daily paid cap, none of which appear on the current page. The
published agent guide on 2026-11-25 remains the final confirmation,
so these values stay labelled with their source until the guide is
reconciled at the opening.
=====================================================================
"""

# At most this many submissions per agent per market, counted across
# the whole competition (settled rule, 2026-11-24 live reads).
MAX_SUBMISSIONS_PER_MARKET = 3

# Each submission carries at most this many files (attachments)
# alongside the evidence note (settled rule, 2026-11-24 live reads).
MAX_ATTACHMENTS_PER_SUBMISSION = 3

# Qualification floor, informational only: an entrant qualifies with
# at least this many judged submissions spread across at least this
# many markets (settled rule, 2026-11-24 live reads). The CLI reports
# progress toward these numbers from the state file.
QUALIFICATION_MIN_JUDGED_SUBMISSIONS = 10
QUALIFICATION_MIN_MARKETS = 3

# Local timezone for calendar questions such as whether a source
# publication date is in the future.
LOCAL_TIMEZONE = "Africa/Lagos"

# Confidence is optional in the model: the current page does not
# mention it, and the published guide may define the real schema.
# When a confidence is supplied it is a score in this closed range.
CONFIDENCE_MIN = 0.0
CONFIDENCE_MAX = 1.0

# Delphi competition markets are Yes or No questions; a submission
# backs exactly one outcome.
VALID_OUTCOMES = ("Yes", "No")

# A submission needs at least one evidence item. Each item must carry
# a source URL, a summary, a verbatim quote and the source
# publication date. Undated or unsourced material is not evidence.
MIN_EVIDENCE_ITEMS = 1
REQUIRED_EVIDENCE_FIELDS = ("source_url", "summary", "quote", "published_date")
