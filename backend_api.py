import uvicorn
import shutil
import json
import uuid
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import traceback 
from langfuse.callback import CallbackHandler

# Import Core Logic
from main_workflow import build_graph
from rag_agents.workflow import rag_app
from agents.indexing_tool import index_invoice_text
from dotenv import load_dotenv

load_dotenv()
# Paths
BASE_DIR = Path(__file__).resolve().parent
WEB_UPLOAD_DIR = BASE_DIR / "data" / "web_uploads" 
INCOMING_DIR = BASE_DIR / "data" / "incoming" 
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORTS_DIR = BASE_DIR / "outputs" / "reports"

# Ensure directories exist
WEB_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INCOMING_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Initialize API
app = FastAPI(title="Lumina Invoice Auditor API", version="1.0.0")

# CORS (Allow React to talk to Python)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models (Data Structures) ---
class ChatRequest(BaseModel):
    question: str
    history: List[str] = []

class ActionRequest(BaseModel):
    invoice_id: str
    action: str 
    notes: Optional[str] = ""

class RerunRequest(BaseModel):
    invoice_id: str
    updated_data: Dict[str, Any]

class ProcessRequest(BaseModel):
    filename: str

# --- ENDPOINTS ---

@app.get("/")
def health_check():
    return {"status": "online", "system": "Lumina Auditor Backend"}

@app.post("/api/upload")
async def upload_invoice(file: UploadFile = File(...)):
    """
    1. Saves file
    2. Runs LangGraph Workflow
    3. Indexes for RAG
    4. MOVES file to processed folder <--- NEW
    5. Returns Result
    """
    try:
        # 1. Save File
        file_path = INCOMING_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f" [API] Processing: {file.filename}")

        langfuse_handler = CallbackHandler()
        
        # 2. Run Workflow
        workflow = build_graph()
        final_state = workflow.invoke({"status": "STARTING", "file_name": file.filename},config={"callbacks": [langfuse_handler]})
        
        # 3. Index for RAG
        if final_state.get("raw_text"):
            audit = final_state.get("structured_data", {})
            status = "PASS" if final_state.get("is_valid") else "FAIL"
            issues = final_state.get("discrepancies", [])
            
            context = f"""
            INVOICE: {file.filename}
            STATUS: {status}
            VENDOR: {audit.get('vendor_name')}
            ISSUES: {issues}
            RAW TEXT: {final_state['raw_text']}
            """
            index_invoice_text(context, {"source": file.filename})

        # --- 4. NEW: FILE LIFECYCLE MANAGEMENT ---
        # Move the file to 'processed' only if we reached this point successfully
        destination_path = PROCESSED_DIR / file.filename
        
        # Check for duplicates and rename if necessary (e.g., "invoice.pdf" -> "uuid_invoice.pdf")
        if destination_path.exists():
            timestamp = uuid.uuid4().hex[:8]
            destination_path = PROCESSED_DIR / f"{timestamp}_{file.filename}"
            
        shutil.move(str(file_path), str(destination_path))
        print(f" [API] Archived {file.filename} to processed folder.")
        # -----------------------------------------

        return {
            "status": "success",
            "filename": file.filename,
            "data": final_state.get("structured_data"),
            "validation": {
                "is_valid": final_state.get("is_valid"),
                "discrepancies": final_state.get("discrepancies")
            },
            "report_html": final_state.get("final_report_html")
        }

    except Exception as e:
        print(f"Error: {e}")
        # Optional: You could delete the file from 'incoming' if processing fails so it doesn't get stuck
        # if file_path.exists():
        #    os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports")
def get_reports():
    """Returns list of all processed JSON reports"""
    reports = []
    # Sort by newest
    files = sorted(REPORTS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    for f in files:
        try:
            with open(f, "r") as jf:
                reports.append(json.load(jf))
        except: pass
    return reports

@app.post("/api/chat")
def chat_agent(req: ChatRequest):
    """RAG Chatbot Endpoint"""
    try:
        print(f" [API] Chat Request: {req.question}") # Debug print
        
        # Format history string for the agent
        hist_str = [f"{msg}" for msg in req.history]
        
        # RUN THE AGENT
        result = rag_app.invoke({"question": req.question, "chat_history": hist_str})
        
        return {
            "answer": result.get("answer", "No answer"),
            "score": result.get("reflection_score", {}),
            "is_safe": result.get("reflection_score", {}).get("is_safe", False)
        }
    except Exception as e:
        print("!!! CHAT ENDPOINT ERROR !!!")
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=f"Backend Error: {str(e)}")

@app.post("/api/action")
def human_action(req: ActionRequest):
    """Handle Manual Approve/Reject"""
    json_path = REPORTS_DIR / f"{req.invoice_id}.json"
    
    if not json_path.exists():
        raise HTTPException(404, "Report not found")
        
    with open(json_path, "r") as f:
        data = json.load(f)
        
    data["status"] = "Approved" if req.action == "APPROVE" else "Rejected"
    data["human_readable_summary"] += f" (Manually {req.action}: {req.notes})"
    
    with open(json_path, "w") as f:
        json.dump(data, f)
        
    return {"status": "success", "new_state": data["status"]}

@app.post("/api/rerun")
def rerun_validation(req: RerunRequest):
    """Edit Data and Re-run Workflow"""
    try:
        print(f" [API] Re-running {req.invoice_id} with new data...")
        workflow = build_graph()
        
        rerun_state = {
            "is_rerun": True,
            "corrected_data": req.updated_data,
            "status": "STARTING",
            "file_name": req.invoice_id,
            "file_path": "manual_override",
            "raw_text": ""
        }
        
        final_state = workflow.invoke(rerun_state)
        
        # Update JSON if passed
        if final_state.get("is_valid"):
            json_path = REPORTS_DIR / f"{req.invoice_id}.json"
            if json_path.exists():
                with open(json_path, "r") as f: data = json.load(f)
                data["status"] = "Approved"
                data["audit_trail"]["invoice_data"] = req.updated_data
                data["human_readable_summary"] = "Re-run Passed (Manual Data)"
                with open(json_path, "w") as f: json.dump(data, f)

        return {
            "is_valid": final_state.get("is_valid"),
            "discrepancies": final_state.get("discrepancies")
        }
    except Exception as e:
        raise HTTPException(500, str(e))
    
@app.get("/api/download/{filename}")
def download_report(filename: str):
    """Serves the generated HTML report to the frontend."""
    file_path = REPORTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path=file_path, filename=filename, media_type='text/html')

@app.get("/api/incoming-files")
def list_incoming_files():
    """List raw files waiting in the incoming folder"""
    files = []
    valid_exts = {'.pdf', '.png', '.jpg', '.jpeg'}
    
    # Scan directory
    for f in INCOMING_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in valid_exts:
            stats = f.stat()
            files.append({
                "name": f.name,
                "size": f"{round(stats.st_size / 1024, 2)} KB",
                "date": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")
            })
    
    # Return newest first
    return sorted(files, key=lambda x: x['date'], reverse=True)

# --- NEW: Process Existing File ---
@app.post("/api/process-existing")
async def process_existing_file(req: ProcessRequest):
    """Manually trigger workflow for a file already in INCOMING"""
    filename = req.filename
    file_path = INCOMING_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(404, "File not found in incoming folder")
    
    print(f" [API] Manually triggering existing file: {filename}")
    
    try:
        # 1. Run Workflow
        # We pass the full path so the workflow knows exactly where to find it
        workflow = build_graph()
        final_state = workflow.invoke({
            "status": "STARTING", 
            "file_name": filename,
            "file_path": str(file_path) 
        })
        
        # 2. Index for RAG
        if final_state.get("raw_text"):
            audit = final_state.get("structured_data", {})
            status = "PASS" if final_state.get("is_valid") else "FAIL"
            issues = final_state.get("discrepancies", [])
            
            context = f"""
            INVOICE: {filename}
            STATUS: {status}
            VENDOR: {audit.get('vendor_name')}
            ISSUES: {issues}
            RAW TEXT: {final_state['raw_text']}
            """
            index_invoice_text(context, {"source": filename})

        # 3. Archive File (Move to Processed)
        destination_path = PROCESSED_DIR / filename
        if destination_path.exists():
            timestamp = uuid.uuid4().hex[:8]
            destination_path = PROCESSED_DIR / f"{timestamp}_{filename}"
            
        shutil.move(str(file_path), str(destination_path))
        print(f" [API] Archived {filename} to processed folder.")

        return {
            "status": "success",
            "filename": filename,
            "data": final_state.get("structured_data"),
            "validation": {
                "is_valid": final_state.get("is_valid"),
                "discrepancies": final_state.get("discrepancies")
            },
            "report_html": final_state.get("final_report_html")
        }
        
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)