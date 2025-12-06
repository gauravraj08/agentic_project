import json
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional

# Import Agents
from agents.extractor_agent import extractor_node
from agents.validation_agent import validation_node
from agents.translation_agent import TranslationAgent
from agents.reporting_agent import ReportingAgent
from protocols.a2a import AgentMessage
from tools.file_watcher import InvoiceWatcherTool

# Define Shared Memory
class InvoiceState(TypedDict):
    file_path: str
    file_name: str
    raw_text: str
    structured_data: Optional[dict]
    validation_results: Dict[str, Any]
    is_valid: bool
    discrepancies: List[str]
    final_report_html: str
    status: str
    error_message: str
    is_rerun: bool
    corrected_data: dict

# --- NODE DEFINITIONS ---

def monitor_node(state):
    print(f"\n--- [1] MONITOR NODE ---")
    # Support for UI-driven file selection
    if state.get("file_name"):
        path = f"data/incoming/{state['file_name']}"
        print(f"   Targeting File: {path}")
        return {"file_path": path, "status": "PROCESSING"}
    
    # Default Watcher logic
    res = InvoiceWatcherTool().execute()
    if res["found"]:
        return {
            "file_path": res["file_path"], 
            "file_name": res["file_name"], 
            "status": "PROCESSING"
        }
    return {"status": "WAITING"}

def extractor_wrapper(state):
    # Wrapper to print debug info
    print(f"\n--- [2] EXTRACTOR NODE ---")
    return extractor_node(state)

def translation_node(state):
    print(f"\n--- [3] TRANSLATOR NODE ---")
    if state.get("status") == "FAILED": 
        print("   Skipping (Previous Step Failed)")
        return {"status": "FAILED"}
    
    agent = TranslationAgent()
    msg = AgentMessage("orch", "trans", "TRANSLATE_EXTRACT", {"raw_text": state["raw_text"]})
    
    # Call Agent (which calls FastMCP Port 8002)
    res = agent.process_message(msg)
    
    if res.status == "SUCCESS": 
        data = res.payload["structured_data"]
        print(f"   DATA EXTRACTED:\n{json.dumps(data, indent=2)}") 
        return {"structured_data": data}
        
    print(f"   TRANSLATION FAILED: {res.payload}")
    return {"status": "FAILED", "error_message": res.payload.get("error")}

def validation_wrapper(state):
    print(f"\n--- [4] VALIDATION NODE ---")
    if state.get("status") == "FAILED": return {"status": "FAILED"}
    
    # Run the agent logic
    result = validation_node(state)
    
    print(f"   VALIDATION RESULT: {result}")
    return result

def reporting_node(state):
    print(f"\n--- [5] REPORTING NODE ---")
    if state.get("status") == "FAILED": 
        print("   Skipping Report (Status is FAILED)")
        return {"status": "FAILED"}
        
    data = state.get("structured_data")
    if not data: 
        print("   CRITICAL: No Data for Reporting")
        return {"status": "FAILED", "error_message": "No structured data"}
        
    # Merge Full Data with Status
    report_data = data.copy()
    report_data["validation_status"] = "PASS" if state.get("is_valid") else "FAIL"
    report_data["discrepancies"] = state.get("discrepancies", [])
    
    print(f"   Sending Full Data to Reporter ({len(str(report_data))} chars)")
    
    agent = ReportingAgent()
    msg = AgentMessage("orch", "rep", "GENERATE_REPORT", report_data)
    res = agent.process_message(msg)
    
    if res.status == "SUCCESS":
        print("   Report Generated Successfully.")
        return {"final_report_html": res.payload["report_html"], "status": "COMPLETED"}
        
    print(f"   REPORTING FAILED: {res.payload}")
    return {"status": "FAILED", "error_message": res.payload.get("error")}

# --- GRAPH BUILDER ---

def build_graph():
    wf = StateGraph(InvoiceState)
    
    wf.add_node("monitor", monitor_node)
    wf.add_node("extractor", extractor_wrapper)
    wf.add_node("translator", translation_node)
    wf.add_node("validator", validation_wrapper)
    wf.add_node("reporter", reporting_node)
    
    wf.set_entry_point("monitor")
    
    wf.add_edge("monitor", "extractor")
    wf.add_edge("extractor", "translator")
    wf.add_edge("translator", "validator")
    wf.add_edge("validator", "reporter")
    wf.add_edge("reporter", END)
    
    return wf.compile()