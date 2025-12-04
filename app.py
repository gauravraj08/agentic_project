import streamlit as st
import json
import time
from pathlib import Path
import sys

# --- SETUP ---
root_file = Path(__file__).resolve()
project_root = root_file.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from main_workflow import build_graph
from rag_agents.workflow import rag_app
from agents.indexing_tool import index_invoice_text

# Paths
BASE_DIR = Path(__file__).resolve().parent
INCOMING_PATH = BASE_DIR / "data" / "incoming"
REPORTS_PATH = BASE_DIR / "outputs" / "reports"
INCOMING_PATH.mkdir(parents=True, exist_ok=True)
REPORTS_PATH.mkdir(parents=True, exist_ok=True)

# --- CONFIG ---
st.set_page_config(page_title="AI Invoice Auditor", layout="wide", page_icon="🧾")

st.markdown("""
<style>
    /* Sidebar Text Color Fix */
    section[data-testid="stSidebar"] .css-10trblm { color: #FFFFFF !important; }
    section[data-testid="stSidebar"] span { color: #FFFFFF !important; }
    
    /* Header Styling */
    .infosys-header {
        background-color: white;
        padding: 1.5rem;
        border-bottom: 4px solid #00A9E0;
        margin-bottom: 2rem;
        border-radius: 5px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .infosys-header h1 { color: #0F1A3B; margin: 0; font-size: 2.2rem; }
    .infosys-header p { color: #005691; margin: 5px 0 0 0; }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: white;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class='infosys-header'>
    <h1>🤖 AI Invoice Auditor Dashboard</h1>
    <p>Agentic AI-Powered Multilingual Invoice Validation System</p>
</div>
""", unsafe_allow_html=True)

# --- DATA LOADING ---
def load_reports():
    reports = []
    # Load all JSON metadata files
    for f in sorted(REPORTS_PATH.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with open(f, 'r') as jf:
                data = json.load(jf)
                reports.append((f, data))
        except: pass
    return reports

# Refresh data on every rerun
all_reports = load_reports()

# Filter Queues
manual_queue = [(f, r) for f, r in all_reports if r.get('status') in ["FAIL", "REJECTED", "Manual Review"]]
processed_queue = [(f, r) for f, r in all_reports if r.get('status') in ["PASS", "SUCCESS", "Approved", "Rejected"]]

# --- SIDEBAR ---
st.sidebar.markdown("### ⚙️ Auditor Tools")
selection = st.sidebar.radio(
    "Go to:",
    [
        "Upload Invoices",
        f"Human Action Queue ({len(manual_queue)})", 
        f"Processed Reports ({len(processed_queue)})", 
        "Invoice Q&A (RAG)"
    ]
)

# --- 1. UPLOAD ---
if selection == "Upload Invoices":
    st.subheader("📤 Upload New Invoices")
    
    with st.container():
        uploaded_files = st.file_uploader("Drop PDF/Images here", accept_multiple_files=True)
        if uploaded_files:
            for f in uploaded_files:
                (INCOMING_PATH / f.name).write_bytes(f.getbuffer())
            st.success(f"Uploaded {len(uploaded_files)} files.")
            time.sleep(1)
            st.rerun()

    st.subheader("🕒 Files Awaiting Processing")
    files = list(INCOMING_PATH.glob("*.*"))
    if not files:
        st.info("Queue is empty.")
    else:
        for f in files:
            col1, col2 = st.columns([3, 1])
            col1.write(f"📄 **{f.name}**")
            if col2.button("▶ Process", key=f.name):
                with st.spinner("Agents Running..."):
                    app = build_graph()
                    # Run Workflow
                    final_state = app.invoke({"status": "STARTING", "file_name": f.name})
                    
                    # RAG Indexing
                    if final_state.get("raw_text"):
                        # Construct a "Rich Context" string
                        audit_data = final_state.get("structured_data", {})
                        discrepancies = final_state.get("discrepancies", [])
                        status = "APPROVED" if final_state.get("is_valid") else "REJECTED"
                            
                        rich_context = f"""
                        --- INVOICE AUDIT RECORD ---
                        Filename: {f.name}
                        Invoice No: {audit_data.get('invoice_no', 'Unknown')}
                        Vendor: {audit_data.get('vendor_name', 'Unknown')}
                            
                        STATUS: {status}
                            
                        AUDITOR NOTES / DISCREPANCIES:
                        {chr(10).join([f"- {d}" for d in discrepancies])}
                            
                        --- RAW INVOICE TEXT ---
                        {final_state.get("raw_text")}
                        """

                        index_invoice_text(rich_context, {"source": f.name})

                    time.sleep(1)
                    st.rerun()

# --- 2. HUMAN QUEUE (FAILURES) ---
elif selection.startswith("Human Action Queue"):
    st.subheader("⚠️ Manual Review Required")
    
    if not manual_queue:
        st.success("No pending reviews.")
    
    for r_file, data in manual_queue:
        invoice_id = data.get('invoice_id', 'Unknown')
        summary = data.get('human_readable_summary', 'No summary.')
        
        with st.expander(f"🛑 {invoice_id}", expanded=True):
            st.error(f"Reason: {summary}")
            
            c1, c2 = st.columns(2)
            if c1.button("Force Approve", key=f"app_{invoice_id}"):
                data['status'] = "Approved"
                data['human_readable_summary'] += " (Manually Approved)"
                with open(r_file, 'w') as f: json.dump(data, f)
                st.rerun()
                
            if c2.button("Confirm Reject", key=f"rej_{invoice_id}"):
                data['status'] = "Rejected"
                with open(r_file, 'w') as f: json.dump(data, f)
                st.rerun()

# --- 3. PROCESSED REPORTS (SUMMARY & DOWNLOAD) ---
elif selection.startswith("Processed Reports"):
    st.subheader("✅ Completed Audits")
    
    if not processed_queue:
        st.info("No processed reports found.")
        
    for r_file, data in processed_queue:
        invoice_id = data.get('invoice_id', 'Unknown')
        status = data.get('status', 'Unknown')
        summary = data.get('human_readable_summary', '')
        
        # Color coding the expander
        label_color = "green" if status in ["Approved", "PASS", "SUCCESS"] else "red"
        
        with st.expander(f":{label_color}[{invoice_id} - {status}]"):
            st.markdown(f"**Summary:** {summary}")
            
            # DOWNLOAD BUTTON
            html_path_str = data.get('html_report_path')
            if html_path_str and Path(html_path_str).exists():
                with open(html_path_str, "r", encoding="utf-8") as f:
                    st.download_button(
                        label="📥 Download HTML Report",
                        data=f.read(),
                        file_name=f"{invoice_id}_Report.html",
                        mime="text/html",
                        key=f"dl_{invoice_id}"
                    )
            else:
                st.warning("Report file missing.")
                
            st.divider()
            st.caption("Raw Data:")
            st.json(data.get("audit_trail", {}).get("invoice_data", {}))

# --- 4. RAG CHAT ---
elif selection == "Invoice Q&A (RAG)":
    st.subheader("💬 Chat with Data")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])

    if prompt := st.chat_input("Ask about invoices..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                hist = [f"{m['role']}: {m['content']}" for m in st.session_state.messages]
                result = rag_app.invoke({"question": prompt, "chat_history": hist})
                
                ans = result.get("answer", "No answer.")
                score = result.get("reflection_score", {})
                
                final_msg = f"{ans}\n\n*(Confidence: {score.get('score', 0)})*" if score.get("is_safe") else f"⚠️ I cannot answer this.\nReason: {score.get('reason')}"
                
                st.markdown(final_msg)
                st.session_state.messages.append({"role": "assistant", "content": final_msg})
            except Exception as e:
                st.error(f"Error: {e}")