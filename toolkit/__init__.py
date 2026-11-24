"""Agent Arena evidence submission toolkit for Jarvis.

Builds and validates Delphi evidence submissions locally against
the competition rules (see rules.py) before anything is sent. The
sending layer (sender.py) is a stub until the official agent guide
publishes on 25 November 2026.
"""

try:
    from . import rules
    from .sender import NotWiredError, send_submission
    from .state import SubmissionState
    from .submission import EvidenceItem, Submission, validate_submission
except ImportError:  # loose script use inside the toolkit directory
    import rules
    from sender import NotWiredError, send_submission
    from state import SubmissionState
    from submission import EvidenceItem, Submission, validate_submission

__all__ = [
    "rules",
    "EvidenceItem",
    "Submission",
    "SubmissionState",
    "validate_submission",
    "send_submission",
    "NotWiredError",
]
