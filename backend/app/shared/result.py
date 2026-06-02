from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=Exception)


@dataclass
class Ok(Generic[T]):
    value: T
    ok: bool = True


@dataclass
class Err(Generic[E]):
    error: E
    ok: bool = False


Result = Ok[T] | Err[E]
