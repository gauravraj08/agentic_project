import json
from protocols.a2a import AgentMessage
from protocols.mcp_client import sync_mcp_call
from utils.logger import get_logger

logger = get_logger("AGENT_TRANSLATOR")
MCP_SERVER_PORT = 8002

class TranslationAgent:
    def __init__(self): self.name = "translation_agent"

    def process_message(self, message: AgentMessage) -> AgentMessage:
        raw_text = message.payload.get("raw_text", "")
        if not raw_text: 
            return self._error(message, "No text provided")

        logger.info(f"Calling FastMCP ({MCP_SERVER_PORT})...")
        res_str = sync_mcp_call(MCP_SERVER_PORT, "translate_invoice", {"raw_text": raw_text})
        
        try:
            if isinstance(res_str, str):
                clean_str = res_str.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_str)
            else:
                data = res_str
            
            if "error" in data:
                return self._error(message, data["error"])
                
            logger.info("Translation Success")
            
            # Return SUCCESS explicitly
            return AgentMessage(
                sender=self.name, 
                receiver=message.sender, 
                task_type="TRANSLATION_RESULT", 
                payload={"structured_data": data}, 
                status="SUCCESS" 
            )
            
        except Exception as e:
            return self._error(message, str(e))

    def _error(self, msg, err):
        return AgentMessage(
            sender=self.name, 
            receiver=msg.sender, 
            task_type="ERROR", 
            payload={"error": err}, 
            status="ERROR"
        )