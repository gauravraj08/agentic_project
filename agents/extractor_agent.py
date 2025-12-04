from tools.ocr_engine import DataHarvesterTool

def extractor_node(state: dict) -> dict:
    """
    Runs Hybrid OCR on the file.
    Supports skipping OCR if this is a Re-Run with corrected data.
    """
    # Check if this is a Re-Run initiated by the Human
    if state.get("is_rerun") and state.get("corrected_data"):
        print(" [Workflow] Extractor: Skipping OCR (Using Human Corrected Data)...")
        # Pass the corrected data through as if it was extracted
        return {
            "raw_text": "Human Corrected Data", 
            "structured_data": state["corrected_data"]
        }

    # Normal Flow
    print(f" [Workflow] Extractor: Reading {state['file_name']}...")
    tool = DataHarvesterTool()
    result = tool.execute(state['file_path'])
    
    if result["status"] == "success":
        return {"raw_text": result["text"]}
    else:
        return {
            "status": "FAILED", 
            "error_message": f"OCR Failed: {result.get('message')}"
        }