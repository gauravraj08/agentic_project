import json
from protocols.mcp_client import sync_mcp_call
from persona.persona_agent import load_rules
from utils.logger import get_logger

logger = get_logger("AGENT_VALIDATOR")
MCP_SERVER_PORT = 8001

def validation_node(state: dict) -> dict:
    data = state.get("structured_data")
    if not data: 
        logger.error("No Data Received")
        return {"status": "FAILED", "error_message": "No Data"}

    # 1. FIND PO NUMBER
    po_number = None
    line_items = data.get('line_items', [])
    
    # Scan header first, then items
    if data.get('po_number'):
        po_number = data.get('po_number')
    else:
        for item in line_items:
            val = item.get('po_number')
            if val and str(val).lower() not in ['none', 'null', '']:
                po_number = val
                break
            
    if not po_number:
        logger.warning("❌ NO PO NUMBER FOUND. Skipping Remote Validation.")
        return {"discrepancies": ["Missing PO Number in Invoice Data"], "is_valid": False}

    # 2. CALL REMOTE SERVER
    logger.info(f"Calling FastMCP (Port {MCP_SERVER_PORT}) to validate {po_number}...")
    
    try:
        res_str = sync_mcp_call(MCP_SERVER_PORT, "validate_business_data", {"validation_type": "po", "key": po_number})
        
        # Parse Response
        if isinstance(res_str, str):
            if "Error" in res_str and not res_str.strip().startswith("{"): raise Exception(res_str)
            res = json.loads(res_str)
        else:
            res = res_str
            
        logger.info(f"Remote Result: {res}")
        
        discrepancies = []
        if not res.get("valid"):
            discrepancies.append(f"Invalid PO Number: {po_number} (Not found in ERP)")
            
        return {"discrepancies": discrepancies, "is_valid": len(discrepancies) == 0}
        
    except Exception as e:
        logger.error(f"Validation Crash: {e}")
        return {"discrepancies": [f"System Error: {e}"], "is_valid": False}