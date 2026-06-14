from __future__ import annotations

from botocore.exceptions import ClientError

_CONDITIONAL_FAILURE_CODE = "ConditionalCheckFailed"
_TRANSACTION_CONDITION_CODES = (
    "TransactionCanceledException",
    "ConditionalCheckFailedException",
)


class ExtraTransactionConditionFailedError(Exception):
    """A conditional check failed for a transaction item owned by another adapter."""


def cancellation_reasons(exc: ClientError) -> list[dict[str, str]]:
    return [
        {"code": reason.get("Code", "None"), "msg": reason.get("Message", "")}
        for reason in exc.response.get("CancellationReasons", [])
    ]


def conditional_failure_indexes(exc: ClientError) -> set[int]:
    code = exc.response["Error"]["Code"]
    if code not in _TRANSACTION_CONDITION_CODES:
        return set()

    reasons = exc.response.get("CancellationReasons", [])
    if reasons:
        return {
            index
            for index, reason in enumerate(reasons)
            if reason.get("Code") == _CONDITIONAL_FAILURE_CODE
        }

    if code == "ConditionalCheckFailedException":
        return {0}

    return set()


def has_conditional_failure_at(exc: ClientError, indexes: set[int]) -> bool:
    return bool(conditional_failure_indexes(exc) & indexes)
