from __future__ import annotations


class JobCancelled(RuntimeError):
    """Raised when a queued or running transcription job is cancelled."""
