from dataclasses import dataclass, asdict, field
from typing import Any, Dict
import uuid
from datetime import datetime

@dataclass
class AgentMessage:
    sender: str
    receiver: str
    task_type: str
    payload: Dict[str, Any]
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "PENDING"

    def to_json(self):
        return asdict(self)