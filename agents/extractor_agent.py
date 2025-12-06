import json
from protocols.mcp_client import sync_mcp_call
from utils.logger import get_logger

logger = get_logger("AGENT_EXTRACTOR")
MCP_SERVER_PORT = 8001

def extractor_node(state: dict) -> dict:
    # 1. Check for Human Override (Re-run)
    if state.get("is_rerun") and state.get("corrected_data"):
        logger.info("Skipping OCR (Using Human Data)")
        return {
            "raw_text": "Human Corrected Data", 
            "structured_data": state["corrected_data"],
            "status": "PROCESSING"
        }

    logger.info(f"Calling FastMCP ({MCP_SERVER_PORT})...")
    
    # 2. Call Remote Tool
    res_str = sync_mcp_call(MCP_SERVER_PORT, "ocr_extract", {"file_path": state['file_path']})
    
    # 3. Process Result
    try:
        # Parse JSON response
        res = json.loads(res_str) if isinstance(res_str, str) else res_str
        
        if res.get("status") == "success": 
            logger.info("OCR Success")
            return {"raw_text": res["text"]}
        
        # FAIL CASE: OCR returned error
        logger.error(f"OCR Failed: {res.get('message')}")
        return {
            "status": "FAILED", 
            "error_message": res.get("message", "Unknown OCR Error"),
            "raw_text": "" # Safety key to prevent crashes downstream
        }
            
    except Exception as e:
        logger.critical(f"CRASH: {e}")
        return {
            "status": "FAILED", 
            "error_message": f"Extractor Crash: {e}",
            "raw_text": "" 
        }