"""
Standard SSE Event Schemas.
"""
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class SSEEventType(str, Enum):
    PROGRESS = "progress"
    SOURCE_STATUS = "source_status"
    RESULT = "result"
    ERROR = "error"


class SSEEvent(BaseModel):
    event: SSEEventType
    data: Any
    id: Optional[str] = None
    retry: Optional[int] = None

    def to_sse_format(self) -> str:
        """Format as raw SSE line string."""
        import json
        payload = json.dumps(self.data) if not isinstance(self.data, str) else self.data
        return f"event: {self.event.value}\ndata: {payload}\n\n"
