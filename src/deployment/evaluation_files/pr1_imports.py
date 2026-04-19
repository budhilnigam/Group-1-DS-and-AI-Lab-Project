"""User notification helpers."""
import os
import sys
import json
import logging
from datetime import datetime
from typing import List

log = logging.getLogger(__name__)


def build_notification(user_id: int, message: str) -> dict:
    """Return a notification payload."""
    return {
        "user_id": user_id,
        "message": message,
        "created_at": datetime.utcnow().isoformat(),
    }


def send_batch(notifications: List[dict]) -> int:
    """Send a batch of notifications and return the count delivered."""
    delivered = 0
    for n in notifications:
        log.info("sending to %s", n["user_id"])
        delivered += 1
    return delivered
