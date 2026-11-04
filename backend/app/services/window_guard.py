from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional

WINDOW_DURATION_HOURS = 24.0
WINDOW_DURATION_SECONDS = WINDOW_DURATION_HOURS * 3600.0

class MessagingWindowExpiredError(Exception):
    """Raised when an outgoing Facebook Messenger reply is attempted outside the 24-hour standard window."""
    def __init__(self, message: str, hours_elapsed: float):
        super().__init__(message)
        self.message = message
        self.hours_elapsed = hours_elapsed

def check_messaging_window(last_customer_message_at: Optional[datetime]) -> Tuple[bool, float, str]:
    """
    Evaluates Meta Messenger's 24-hour Standard Messaging Window policy.
    Reference: https://developers.facebook.com/docs/messenger-platform/overview#standard_messaging

    Returns:
        (is_allowed: bool, hours_remaining: float, explanation: str)
    """
    if not last_customer_message_at:
        return False, 0.0, "Blocked: No previous customer message recorded in this thread."

    # Ensure timezone awareness (UTC)
    if last_customer_message_at.tzinfo is None:
        last_customer_msg_utc = last_customer_message_at.replace(tzinfo=timezone.utc)
    else:
        last_customer_msg_utc = last_customer_message_at

    now_utc = datetime.now(timezone.utc)
    elapsed_seconds = (now_utc - last_customer_msg_utc).total_seconds()

    if elapsed_seconds < 0:
        elapsed_seconds = 0.0

    hours_elapsed = round(elapsed_seconds / 3600.0, 2)
    seconds_remaining = WINDOW_DURATION_SECONDS - elapsed_seconds

    if seconds_remaining > 0:
        hours_remaining = round(seconds_remaining / 3600.0, 1)
        return True, hours_remaining, f"Within standard messaging window ({hours_remaining}h remaining)."
    else:
        return False, 0.0, (
            f"Blocked: Customer last messaged {hours_elapsed}h ago. "
            f"Standard 24-hour messaging window has expired. "
            f"Customer must message again or an approved Meta Message Tag must be used."
        )

def validate_send_allowed(last_customer_message_at: Optional[datetime]) -> None:
    """Raises MessagingWindowExpiredError if outside the 24-hour window."""
    is_allowed, hours_remaining, explanation = check_messaging_window(last_customer_message_at)
    if not is_allowed:
        hours_elapsed = 24.0
        if last_customer_message_at:
            if last_customer_message_at.tzinfo is None:
                last_utc = last_customer_message_at.replace(tzinfo=timezone.utc)
            else:
                last_utc = last_customer_message_at
            hours_elapsed = round((datetime.now(timezone.utc) - last_utc).total_seconds() / 3600.0, 2)
        raise MessagingWindowExpiredError(explanation, hours_elapsed=hours_elapsed)
