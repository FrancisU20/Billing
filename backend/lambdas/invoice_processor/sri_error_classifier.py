from __future__ import annotations

"""Backward-compatible facade for SRI error classification."""

from lambdas.invoice_processor.sri_error_mapper import PERMANENT, RETRYABLE, classify

__all__ = ["PERMANENT", "RETRYABLE", "classify"]
