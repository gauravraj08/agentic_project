import json
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
import os

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

# def monitor_node(state):
#     print(f"\n--- [1] MONITOR NODE ---")
    
#     # --- A. WEB UPLOAD LOGIC (React) ---
#     if state.get("file_name"):
#         # The API saves to 'data/web_uploads', so we must look there
#         web_path = f"data/web_uploads/{state['file_name']}"
        
#         if os.path.exists(web_path):
#             print(f"   Targeting Web Upload: {web_path}")
#             return {
#                 "file_path": web_path, 
#                 "status": "PROCESSING",
#                 # For web uploads, original name is just the filename
#                 "original_name": state['file_name'] 
#             }
#         else:
#             print(f"   ❌ ERROR: File missing: {web_path}")
#             return {"status": "FAILED", "error_message": "File not found"}
    
#     # --- B. WATCHER LOGIC (Background) ---
#     # This finds a file and renames it to *.processing
#     res = InvoiceWatcherTool().execute()
    
#     if res["found"]:
#         return {
#             "file_path": res["file_path"],       # Path to the .processing file
#             "file_name": res["original_name"],   # We use the clean name for the report
#             "original_name": res["original_name"], # Store for cleanup later
#             "status": "PROCESSING"
#         }
        
#     return {"status": "WAITING"}

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


# def monitor_node(state):
#     print(f"\n--- [1] MONITOR NODE ---")
    
#     # 1. PRIORITY: If a full path is provided (e.g., from the Background Watcher)
#     # The watcher moves files to 'processed' before calling this, so we trust the path.
#     if state.get("file_path"):
#         print(f"   Using existing path: {state['file_path']}")
#         return {"status": "PROCESSING"}

#     # 2. WEB API: If only a filename is provided (from React/FastAPI)
#     # The API saves new files to 'data/web_uploads', so we must look there.
#     if state.get("file_name"):
#         web_path = f"data/web_uploads/{state['file_name']}"
        
#         # Safety Check: Verify file exists
#         if os.path.exists(web_path):
#             print(f"   Targeting Web Upload: {web_path}")
#             return {"file_path": web_path, "status": "PROCESSING"}
#         else:
#             print(f"   ❌ ERROR: File not found in web_uploads: {web_path}")
#             return {"status": "FAILED", "error_message": "File missing from upload folder"}
    
#     # 3. INTERNAL WATCHER (Optional fallback)
#     # This checks 'data/incoming' if no input was given
#     res = InvoiceWatcherTool().execute()
#     if res["found"]:
#         return {
#             "file_path": res["file_path"], 
#             "file_name": res["file_name"], 
#             "status": "PROCESSING"
#         }
        
#     return {"status": "WAITING"}

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

# def reporting_node(state):
#     print(f"\n--- [5] REPORTING NODE ---")
#     if state.get("status") == "FAILED": 
#         print("   Skipping Report (Status is FAILED)")
#         return {"status": "FAILED"}
        
#     data = state.get("structured_data")
#     if not data: 
#         print("   CRITICAL: No Data for Reporting")
#         return {"status": "FAILED", "error_message": "No structured data"}
        
#     # Merge Full Data with Status
#     report_data = data.copy()
#     report_data["validation_status"] = "PASS" if state.get("is_valid") else "FAIL"
#     report_data["discrepancies"] = state.get("discrepancies", [])
    
#     print(f"   Sending Full Data to Reporter ({len(str(report_data))} chars)")
    
#     agent = ReportingAgent()
#     msg = AgentMessage("orch", "rep", "GENERATE_REPORT", report_data)
#     res = agent.process_message(msg)
    
#     if res.status == "SUCCESS":
#         print("   Report Generated Successfully.")
        
#         # --- NEW: CLEANUP & ARCHIVE ---
#         # This moves the file from incoming/web_uploads -> processed
#         if state.get("file_path") and os.path.exists(state["file_path"]):
#             watcher = InvoiceWatcherTool()
#             print(f"   Archiving file to processed folder...")
#             watcher.move_to_processed(
#                 current_path_str=state["file_path"], 
#                 original_name=state.get("original_name")
#             )
            
#         return {"final_report_html": res.payload["report_html"], "status": "COMPLETED"}
        
#     print(f"   REPORTING FAILED: {res.payload}")
#     return {"status": "FAILED", "error_message": res.payload.get("error")}

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