import json
import uuid
import ast
from pathlib import Path
from datetime import datetime
from protocols.a2a import AgentMessage
from protocols.mcp_client import sync_mcp_call
from utils.logger import get_logger

# Initialize Logger
logger = get_logger("AGENT_REPORTER")

# Configuration
MCP_SERVER_PORT = 8002
REPORTS_DIR = Path("outputs/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

class ReportingAgent:
    def __init__(self):
        self.name = "reporting_agent"
        logger.debug("Reporting Agent Initialized")

    def process_message(self, message: AgentMessage) -> AgentMessage:
        logger.info("--- Starting Reporting Process ---")
        
        # 1. Validate Input
        if message.task_type != "GENERATE_REPORT":
            return self._error(message, "Invalid Task Type")
            
        data = message.payload
        if not data:
            return self._error(message, "No data provided for reporting")

        # 2. Prepare Data for Remote Call
        safe_data = str(data)
        logger.info(f"Calling FastMCP (Port {MCP_SERVER_PORT})... Data Size: {len(safe_data)} chars")
        
        try:
            # 3. Call Remote Server (Google ADK Tools) to get HTML
            res_str = sync_mcp_call(MCP_SERVER_PORT, "generate_report", {"report_data": safe_data})
            
            # 4. Parse Response
            if isinstance(res_str, str):
                if "Error" in res_str and not res_str.strip().startswith("{"):
                    logger.error(f"Server returned error string: {res_str}")
                    return self._error(message, res_str)
                
                # Clean Markdown if the LLM added it
                clean = res_str.replace("```json", "").replace("```", "").strip()
                res = json.loads(clean)
            else:
                res = res_str
                
            report_html = res.get("html", "<b>Error: No HTML returned from AI</b>")
            
            # 5. Generate Filenames
            inv_num = data.get('invoice_no')
            
            # Create a safe filename
            if inv_num and str(inv_num).lower() not in ["none", "null", ""]:
                safe_id = "".join([c for c in str(inv_num) if c.isalnum() or c in ('-','_')])
            else:
                safe_id = f"Unknown_{uuid.uuid4().hex[:8]}"

            html_filename = f"{safe_id}.html"
            json_filename = f"{safe_id}.json"
            
            html_path = REPORTS_DIR / html_filename
            json_path = REPORTS_DIR / json_filename
            
            # 6. Generate Human Readable Summary (THE FIX)
            status = data.get('validation_status', 'Unknown')
            discrepancies = data.get('discrepancies', [])
            
            if status in ["PASS", "Approved", "SUCCESS"]:
                summary = f"✅ Approved: {data.get('vendor_name', 'Unknown Vendor')} | {data.get('currency', '$')}{data.get('total_amount', '0')}"
            else:
                # Use the first discrepancy as the summary headline
                issue_text = discrepancies[0] if discrepancies else "Unknown Validation Error"
                summary = f"❌ Rejected: {issue_text}"

            # 7. Save Files to Disk
            # Save HTML
            with open(html_path, "w", encoding="utf-8") as f: 
                f.write(report_html)
            
            # Save JSON Metadata
            metadata = {
                "invoice_id": safe_id,
                "original_invoice_no": inv_num,
                "status": status,
                "human_readable_summary": summary, # <--- Contains the real reason now
                "html_report_path": str(html_filename), # Store relative name for API convenience
                "timestamp": datetime.now().isoformat(),
                "audit_trail": {
                    "invoice_data": data,
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            with open(json_path, "w", encoding="utf-8") as f: 
                json.dump(metadata, f, indent=2)

            logger.info(f"Files Saved Successfully: {json_filename}")
            
            # 8. Return Success
            return AgentMessage(
                sender=self.name, 
                receiver=message.sender, 
                task_type="REPORT_RESULT", 
                payload={"report_html": report_html, "final_report": metadata}, 
                status="SUCCESS"
            )
            
        except Exception as e:
            logger.critical(f"Reporting Logic Failed: {str(e)}")
            return self._error(message, str(e))

    def _error(self, msg, err):
        return AgentMessage(
            sender=self.name, 
            receiver=msg.sender, 
            task_type="ERROR", 
            payload={"error": err}, 
            status="ERROR"
        )