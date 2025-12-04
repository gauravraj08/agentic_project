from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Optional
import uuid
from datetime import datetime

@dataclass
class AgentMessage:
    """
    Standard A2A (Agent-to-Agent) Protocol Envelope.
    """
    sender: str              # Who sent it? (e.g., "orchestrator")
    receiver: str            # Who is it for? (e.g., "translator")
    task_type: str           # What to do? (e.g., "TRANSLATE_TEXT")
    payload: Dict[str, Any]  # The actual data (e.g., {"text": "Hola..."})
    
    # Metadata (Auto-generated)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "PENDING"  # PENDING, SUCCESS, ERROR

    def to_json(self):
        return asdict(self)