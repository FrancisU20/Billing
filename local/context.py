"""Mock Lambda context for local execution."""
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class LocalContext:
    function_name:    str = "local"
    function_version: str = "$LATEST"
    aws_request_id:   str = field(default_factory=lambda: str(uuid4()))
    memory_limit_in_mb: int = 256

    def get_remaining_time_in_millis(self) -> int:
        return 900_000
