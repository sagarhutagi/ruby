from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    STEP_START = "step_start"
    STEP_PROGRESS = "step_progress"
    STEP_COMPLETE = "step_complete"
    ACTION_TOOL_CALL = "action_tool_call"
    OBSERVATION_TOOL_RESULT = "observation_tool_result"
    PERMISSION_REQUEST = "permission_request"
    PERMISSION_REPLY = "permission_reply"
    TOKEN_DELTA = "token_delta"
    TASK_STATE_CHANGE = "task_state_change"
    CONTEXT_COMPACTED = "context_compacted"
    AGENT_CANCEL = "agent_cancel"
    AGENT_ERROR = "agent_error"
    AGENT_COMPLETE = "agent_complete"


@dataclass
class AgentEvent:
    type: EventType
    conversation_id: str
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: Optional[str] = None
    step_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "type": self.type.value if isinstance(self.type, Enum) else str(self.type),
            "conversation_id": self.conversation_id,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    def to_sse(self) -> str:
        """Format as standard Server-Sent Event data block."""
        return f"data: {json.dumps(self.to_dict())}\n\n"
