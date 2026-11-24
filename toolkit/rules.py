"""Competition rules constants for the Agent Arena evidence toolkit.

=====================================================================
RULES CONSTANTS: SINGLE SOURCE OF TRUTH
Every rules dependent value in this toolkit lives in this file and
nowhere else. If a rule changes, edit it here and the validator, the
state tracker and the CLI all follow.

Source of these values: the live DoraHacks competition page for the
Gensyn Agent Arena (delphi agent competition), read first hand on
2026-11-23 and recorded in the goal prep notes
(2026-11-23-morning-check.md). A further live read was in progress
when this toolkit was built; if that read corrects any value below,
this file is the one place to change.
=====================================================================
"""

# Agents may only submit evidence on markets whose ID is strictly
# greater than this value (live page: markets with ID over 1000 only).
MIN_MARKET_ID_EXCLUSIVE = 1000

# At most one submission per market per hour (live page rule).
MIN_SECONDS_BETWEEN_SUBMISSIONS_PER_MARKET = 60 * 60

# At most this many paid submissions per calendar day, counted in the
# Africa/Lagos timezone (live page: max 50 paid submissions per day).
MAX_PAID_SUBMISSIONS_PER_DAY = 50
DAILY_COUNT_TIMEZONE = "Africa/Lagos"

# Confidence is a score in this closed range.
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
