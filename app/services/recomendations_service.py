import math

from datetime import datetime
from datetime import timezone

HOURS_TO_DECAY = 48.0
LIKE_WEIGHT = 1.5
DISLIKE_WEIGHT = 1.2
COMMENT_WEIGHT = 0.5

def _compute_hours_since_creation(timestamp: datetime, now: datetime) -> float:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    delta = now - timestamp
    return delta.total_seconds() / 3600.0

def compute_history_score(likes: int, dislikes: int, comments: int, created_at: datetime) -> float:
    now = datetime.now(timezone.utc)
    hours_since_creation = _compute_hours_since_creation(created_at, now)
    decay = math.exp(-hours_since_creation / HOURS_TO_DECAY)
    return (
        (float(likes or 0) * LIKE_WEIGHT) - (float(dislikes or 0) * DISLIKE_WEIGHT) -
        (float(comments or 0) * COMMENT_WEIGHT)
    ) * decay
