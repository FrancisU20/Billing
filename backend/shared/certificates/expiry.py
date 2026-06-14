from __future__ import annotations

SECONDS_PER_DAY = 24 * 60 * 60

# Days-before-expiry thresholds at which the tenant is notified by
# `certificate_expiry_notifier`, evaluated from the largest to the smallest.
CERTIFICATE_EXPIRY_ALERT_THRESHOLDS_DAYS: tuple[int, ...] = (60, 30)
