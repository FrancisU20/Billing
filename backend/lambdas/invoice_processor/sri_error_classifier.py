from __future__ import annotations

"""
Classifies SRI business-error codes as PERMANENT (do not retry — needs manual
intervention) or RETRYABLE (transient SRI-side congestion, safe to retry).

Coverage is intentionally partial — the SRI has ~50 documented error codes. This
covers the most common ones seen in production integrations; unknown codes default
to PERMANENT (safer to require manual review than to retry something unclassified
indefinitely). Anticipated as technical debt in `context/INVOICES.md` — refine with
real production data, do not expand speculatively here.
"""

PERMANENT = "PERMANENT"
RETRYABLE = "RETRYABLE"

# Códigos SRI conocidos de congestión/disponibilidad transitoria del propio servicio.
_RETRYABLE_CODES = {
    "1",
    "2",  # esquema/servicio temporalmente no disponible
    "70",  # ambiente de procesamiento no disponible
}


def classify(code: str) -> str:
    if code in _RETRYABLE_CODES:
        return RETRYABLE
    return PERMANENT
