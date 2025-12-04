import sys
import time
from langgraph.graph import StateGraph, END

# Import Schemas
from schemas import InvoiceState

# Import Nodes
from agents.monitor_agent import monitor_node
from agents.extractor_agent import extractor_node
from agents.validation_agent import validation_node

# Import Google ADK Agents (Wrappers)
from agents.translation_agent import TranslationAgent
from agents.reporting_agent import ReportingAgent
from protocols.a2a import AgentMessage

# In main_workflow.py

def translation_node(state: dict) -> dict:
    print(" [Workflow] Translator: Calling Google ADK...")
    
    # --- DEBUG START ---
    raw_text = state.get("raw_text", "")
    print(f"   [DEBUG] Raw Text Length: {len(raw_text)}")
    print(f"   [DEBUG] Raw Text Snippet: {raw_text[:100].replace(chr(10), ' ')}...") # Print first 100 chars
    
    if len(raw_text.strip()) < 10:
        print("   [ERROR] Text is too short! OCR likely failed.")
        return {"status": "FAILED", "error_message": "OCR failed to extract sufficient text"}
    # --- DEBUG END ---

    agent = TranslationAgent()
    
    msg = AgentMessage(
        sender="orchestrator", 
        receiver="translator", 
        task_type="TRANSLATE_EXTRACT", 
        payload={"raw_text": raw_text}
    )
    
    response = agent.process_message(msg)
    
    if response.status == "SUCCESS":
        data = response.payload["structured_data"]
        # --- DEBUG START ---
        print(f"   [DEBUG] LLM Output: {data}")
        # --- DEBUG END ---
        return {"structured_data": data}
    else:
        return {"status": "FAILED", "error_message": "Translation Failed"}

def reporting_node(state: dict) -> dict:
    print(" [Workflow] Reporter: Generating Summary...")
    
    # Check Data Availability
    data = state.get("structured_data")
    if not data:
        print("   [Error] Reporter: No structured data found.")
        return {"status": "FAILED", "error_message": "No Data"}

    # Prepare Data
    report_data = {
        "vendor_name": data.get("vendor_name"),
        "invoice_no": data.get("invoice_no"),
        "validation_status": "PASS" if state.get("is_valid") else "FAIL",
        "discrepancies": state.get("discrepancies", []),
        "confidence": data.get("translation_confidence", 0.0),
        # Pass full line items for the HTML table
        "line_items": data.get("line_items", []) 
    }
    
    # Call Agent
    agent = ReportingAgent()
    msg = AgentMessage("orchestrator", "reporter", "GENERATE_REPORT", report_data)
    
    response = agent.process_message(msg)
    
    if response.status == "SUCCESS":
        # Return success AND the HTML so UI can render it immediately
        return {
            "final_report_html": response.payload["report_html"], 
            "status": "COMPLETED"
        }
    else:
        # Log the specific error from the agent
        error = response.payload.get('error', 'Unknown Error')
        print(f"   [Error] Reporting Agent Failed: {error}")
        return {"status": "FAILED", "error_message": error}
    
# --- Graph Construction ---
def build_graph():
    workflow = StateGraph(InvoiceState)

    # Add Nodes
    workflow.add_node("monitor", monitor_node)
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("translator", translation_node)
    workflow.add_node("validator", validation_node)
    workflow.add_node("reporter", reporting_node)

    # Define Edges (The Flow)
    workflow.set_entry_point("monitor")

    # Conditional Logic: Did we find a file?
    def check_file_found(state):
        if state.get("status") == "WAITING":
            return "end" # Loop or Stop (For demo we stop, usually loop)
        return "continue"

    workflow.add_conditional_edges(
        "monitor",
        check_file_found,
        {"continue": "extractor", "end": END}
    )

    workflow.add_edge("extractor", "translator")
    workflow.add_edge("translator", "validator")
    workflow.add_edge("validator", "reporter")
    workflow.add_edge("reporter", END)

    return workflow.compile()

# --- Main Execution Entry Point ---
if __name__ == "__main__":
    print("Initializing AI Invoice Auditor Workflow...")
    app = build_graph()
    
    # Initial State
    initial_state = {"status": "STARTING"}
    
    # Run
    for output in app.stream(initial_state):
        pass # The print statements in nodes will show progress
    
    print("\nWorkflow Finished.")