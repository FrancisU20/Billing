"""
Decorator de reintento con backoff exponencial.

Uso para llamadas a servicios externos (SRI, Brevo, Secrets Manager):

    from shared.decorators.retry import retry

    @retry(exceptions=(requests.Timeout, ConnectionError), max_attempts=3)
    def call_sri_soap(xml: str) -> str:
        ...
"""
import functools
import time
from typing import Type

from shared.logger import get_logger

_log = get_logger(__name__)


def retry(
    exceptions:   tuple[Type[Exception], ...],
    max_attempts: int   = 3,
    base_delay:   float = 0.5,
    backoff:      float = 2.0,
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        raise
                    _log.warning(
                        "reintentando llamada",
                        func=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay_s=delay,
                        error=str(exc),
                    )
                    time.sleep(delay)
                    delay *= backoff
        return wrapper
    return decorator
