"""Sending layer for the Agent Arena toolkit.

STUB. The official agent guide, which carries the Delphi API spec,
publishes with the competition materials on 25 November 2026. Until
that spec is read, nothing in this project sends anything anywhere:
calling send_submission raises NotImplementedError on purpose.

When the guide lands, this module is where the wiring goes:
bearer Delphi API key, wallet signature on the submission, an
Idempotency-Key header per submission, and the agent identity
headers (agent name Jarvis, harness, model). The API key itself
arrives through the secure credential flow and is never stored in
this repository or in plain files.
"""

from __future__ import annotations


class NotWiredError(NotImplementedError):
    pass


def send_submission(submission, state=None, state_path=None):
    raise NotWiredError(
        "Delphi API integration waits for the official agent guide "
        "(publishes 25 November 2026). No submission has been sent."
    )
