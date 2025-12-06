import json
from fastmcp import FastMCP
from tools.ocr_engine import DataHarvesterTool
from tools.validator import BusinessValidationTool
from utils.logger import get_logger

# Initialize Logger
logger = get_logger("SERVER_LANGGRAPH_8001")

# Initialize FastMCP Server
mcp = FastMCP("LangGraph Tools")

# Initialize Local Tools (Loaded into memory once at startup)
logger.info("Loading OCR Engine & Validator...")
ocr_tool = DataHarvesterTool()
validator_tool = BusinessValidationTool()

@mcp.tool()
def ocr_extract(file_path: str) -> str:
    """
    Extracts text from a PDF or Image invoice using Hybrid OCR.
    Returns a JSON string to ensure safe transport.
    """
    logger.info(f"📨 REQUEST: OCR for {file_path}")
    
    try:
        # Run the local tool
        result = ocr_tool.execute(file_path)
        
        # Log success/fail logic
        if result.get("status") == "success":
            text_len = len(result.get("text", ""))
            logger.info(f"✅ SUCCESS: OCR extracted {text_len} chars")
        else:
            logger.error(f"❌ FAIL: {result.get('message')}")
            
        # Return as JSON string to prevent serialization issues
        return json.dumps(result)
        
    except Exception as e:
        logger.critical(f"🔥 CRASH: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def validate_business_data(validation_type: str, key: str) -> str:
    """
    Validates PO, Vendor, or SKU against the Mock ERP.
    """
    logger.info(f"📨 REQUEST: Validate {validation_type} -> {key}")
    
    try:
        result = validator_tool.execute(validation_type, key)
        
        is_valid = result.get("valid", False)
        icon = "✅" if is_valid else "❌"
        logger.info(f"{icon} RESULT: {is_valid}")
        
        return json.dumps(result)
        
    except Exception as e:
        logger.critical(f"🔥 CRASH: {e}")
        return json.dumps({"valid": False, "reason": f"Server Error: {e}"})

if __name__ == "__main__":
    logger.info("🚀 STARTING LangGraph FastMCP Server on Port 8001...")
    # transport="sse" enables HTTP/SSE mode required for Remote Agents
    mcp.run(transport="sse", port=8001)