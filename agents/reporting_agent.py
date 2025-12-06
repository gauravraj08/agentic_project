import json
import uuid
from pathlib import Path
from protocols.a2a import AgentMessage
from protocols.mcp_client import sync_mcp_call
from utils.logger import get_logger

logger = get_logger("AGENT_REPORTER")
MCP_SERVER_PORT = 8002
REPORTS_DIR = Path("outputs/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

class ReportingAgent:
    def __init__(self): self.name = "reporting_agent"

    def process_message(self, message: AgentMessage) -> AgentMessage:
        data = message.payload
        # Convert dict to string for transport
        safe_data = str(data)[:15000] 
        
        logger.info(f"Calling FastMCP ({MCP_SERVER_PORT})...")
        
        try:
            res_str = sync_mcp_call(MCP_SERVER_PORT, "generate_report", {"report_data": safe_data})
            
            # Parse Response
            if isinstance(res_str, str):
                if "Error" in res_str and not res_str.strip().startswith("{"): return self._error(message, res_str)
                clean = res_str.replace("```json", "").replace("```", "").strip()
                res = json.loads(clean)
            else:
                res = res_str
                
            report_html = res.get("html", "<b>Error: No HTML returned</b>")
            
            # Save Files Locally (So UI can see them)
            inv_num = data.get('invoice_no')
            safe_id = f"Inv_{uuid.uuid4().hex[:6]}"
            if inv_num and str(inv_num).lower() not in ["none", "null"]:
                safe_id = "".join([c for c in str(inv_num) if c.isalnum() or c in ('-','_')])

            html_path = REPORTS_DIR / f"{safe_id}.html"
            json_path = REPORTS_DIR / f"{safe_id}.json"
            
            with open(html_path, "w", encoding="utf-8") as f: 
                f.write(report_html)
            
            metadata = {
                "invoice_id": safe_id, 
                "status": data.get('validation_status'), 
                "human_readable_summary": f"Audit {safe_id}",
                "html_report_path": str(html_path),
                "audit_trail": {"invoice_data": data}
            }
            with open(json_path, "w", encoding="utf-8") as f: 
                json.dump(metadata, f)

            logger.info("Report Saved Successfully")
            
            return AgentMessage(
                sender=self.name, 
                receiver=message.sender, 
                task_type="REPORT_RESULT", 
                payload={"report_html": report_html}, 
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