import streamlit as st
import json
import time
from pathlib import Path
import sys

# --- SETUP PATHS ---
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
PROCESSED_PATH = BASE_DIR / "data" / "processed"

for p in [INCOMING_PATH, REPORTS_PATH, PROCESSED_PATH]:
    p.mkdir(parents=True, exist_ok=True)

# --- PAGE CONFIG ---
st.set_page_config(page_title="Lumina Auditor", layout="wide", page_icon="✨")

# --- MODERN CSS STYLING (FIXED CONTRAST) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Gradient Header */
    .main-header {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 { color: white !important; margin: 0; font-weight: 700; font-size: 2.5rem; }
    .main-header p { color: #e0e7ff !important; margin-top: 0.5rem; font-size: 1.1rem; }

    /* --- METRIC CARD FIX --- */
    div[data-testid="stMetric"] {
        background-color: white !important;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
    }
    /* Force Label Color (Small text) */
    div[data-testid="stMetricLabel"] p {
        color: #64748b !important; /* Slate Grey */
        font-size: 0.9rem;
    }
    /* Force Value Color (Big number) */
    div[data-testid="stMetricValue"] {
        color: #1e293b !important; /* Dark Slate */
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
    }
    section[data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }

    /* Buttons */
    div.stButton > button {
        background: linear-gradient(to right, #6366f1, #4f46e5);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #1e293b;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER COMPONENT ---
st.markdown("""
<div class='main-header'>
    <h1>✨ Lumina Invoice Auditor</h1>
    <p>AI-Agent Orchestration • RAG Intelligence • Distributed Processing</p>
</div>
""", unsafe_allow_html=True)

# --- DATA LOADERS ---
def load_data():
    reports = []
    for f in sorted(REPORTS_PATH.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with open(f, 'r') as jf: reports.append((f, json.load(jf)))
        except: pass
    return reports

all_data = load_data()
manual_queue = [(f, r) for f, r in all_data if r.get('status') in ["FAIL", "REJECTED", "Manual Review"]]
processed_queue = [(f, r) for f, r in all_data if r.get('status') in ["PASS", "SUCCESS", "Approved", "Rejected"]]

# --- SIDEBAR NAV ---
st.sidebar.markdown("### 🧭 Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Processing Studio", "Audit Vault", "AI Insights"], label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Live Stats")
c1, c2 = st.sidebar.columns(2)
c1.metric("Queue", len(manual_queue))
c2.metric("Archive", len(processed_queue))


# === PAGE 1: DASHBOARD (Overview) ===
if page == "Dashboard":
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Invoices", len(all_data), "+ New")
    col2.metric("Approval Rate", "92%", "+4%")
    col3.metric("Avg Processing", "1.2s", "-0.3s")
    col4.metric("Action Required", len(manual_queue), delta_color="inverse")
    
    st.markdown("### 📅 Recent Activity")
    if not all_data:
        st.info("System is ready. No activity yet.")
    else:
        for f, r in all_data[:5]:
            status = r.get('status')
            icon = "🟢" if status in ["PASS", "Approved", "SUCCESS"] else "🔴"
            st.caption(f"{icon} **{r.get('invoice_id')}** | {r.get('human_readable_summary')}")
            st.progress(100 if status in ["PASS", "Approved"] else 40)


# === PAGE 2: PROCESSING STUDIO (Upload & Run) ===
elif page == "Processing Studio":
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📤 Upload Stream")
        uploaded = st.file_uploader("Drop invoices", accept_multiple_files=True, label_visibility="collapsed")
        if uploaded:
            for f in uploaded: (INCOMING_PATH/f.name).write_bytes(f.getbuffer())
            st.toast(f"Uploaded {len(uploaded)} files!", icon="🚀")
            time.sleep(1)
            st.rerun()
            
    with c2:
        st.subheader("⚙️ Controls")
        if st.button("Reset System"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")
    st.subheader("🔁 Active Pipeline")
    files = list(INCOMING_PATH.glob("*.*"))
    if not files: st.success("✨ All caught up!")
    
    for f in files:
        with st.container():
            col_a, col_b, col_c = st.columns([0.1, 0.7, 0.2])
            col_a.write("📄")
            col_b.write(f"**{f.name}**")
            
            if col_c.button("Run Agents", key=f.name):
                status_box = st.status("🚀 Orchestrating Agents...", expanded=True)
                try:
                    app = build_graph()
                    status_box.write("📡 Connecting to FastMCP Servers...")
                    final = app.invoke({"status": "STARTING", "file_name": f.name})
                    
                    if final.get("raw_text"):
                        status_box.write("🧠 Indexing for RAG...")
                        audit = final.get("structured_data", {})
                        context = f"File: {f.name}\nStatus: {final.get('is_valid')}\nVendor: {audit.get('vendor_name')}\nIssues: {final.get('discrepancies')}\nRaw: {final['raw_text']}"
                        index_invoice_text(context, {"source": f.name})
                    
                    status_box.update(label="Complete!", state="complete", expanded=False)
                    
                    if final.get("is_valid"):
                        st.success("✅ Audit Passed")
                        st.balloons()
                    else:
                        st.error("🛑 Audit Failed: Sent to Queue")
                    
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# === PAGE 3: AUDIT VAULT (Detailed Archive) ===
elif page == "Audit Vault":
    
    tab_review, tab_archive = st.tabs(["⚠️ Review Queue", "🗄️ Archive"])
    
    # -- TAB 1: REVIEW --
    with tab_review:
        if not manual_queue: st.info("No manual reviews pending.")
        
        for r_file, data in manual_queue:
            inv_id = data.get('invoice_id', 'Unknown')
            with st.expander(f"🛑 {inv_id}", expanded=True):
                st.markdown(f"**Reason:** {data.get('human_readable_summary')}")
                
                # Show Data
                st.json(data.get("audit_trail", {}).get("invoice_data", {}))
                
                c1, c2 = st.columns(2)
                if c1.button("Approve", key=f"app_{inv_id}", type="primary"):
                    data['status'] = "Approved"
                    with open(r_file, 'w') as f: json.dump(data, f)
                    st.rerun()
                if c2.button("Reject", key=f"rej_{inv_id}"):
                    data['status'] = "Rejected"
                    with open(r_file, 'w') as f: json.dump(data, f)
                    st.rerun()

    # -- TAB 2: ARCHIVE (Enhanced) --
    with tab_archive:
        if not processed_queue: st.info("Archive is empty.")
        
        for r_file, data in processed_queue:
            inv_id = data.get('invoice_id')
            status = data.get('status')
            
            # Color Icon
            icon = "✅" if status in ["Approved", "PASS", "SUCCESS"] else "❌"
            
            with st.expander(f"{icon} {inv_id}  |  {status}"):
                
                # 1. Summary Header
                st.info(f"**Summary:** {data.get('human_readable_summary')}")
                
                # 2. Download Button
                if path := data.get('html_report_path'):
                    if Path(path).exists():
                        with open(path, "r", encoding="utf-8") as f:
                            st.download_button("📥 Download HTML Report", f.read(), f"{inv_id}.html", "text/html")
                
                st.divider()
                
                # 3. Full Data View (The Feature You Asked For)
                st.markdown("#### 🧾 Invoice Data")
                raw_data = data.get("audit_trail", {}).get("invoice_data", {})
                
                # Clean display of main fields
                c1, c2, c3 = st.columns(3)
                c1.metric("Amount", f"{raw_data.get('currency', '$')} {raw_data.get('total_amount', 0)}")
                c2.metric("Date", raw_data.get('invoice_date', 'N/A'))
                c3.metric("Vendor", raw_data.get('vendor_name', 'N/A'))
                
                # JSON Inspector
                with st.expander("View Raw JSON"):
                    st.json(raw_data)


# === PAGE 4: AI INSIGHTS ===
elif page == "AI Insights":
    st.subheader("💬 Ask the Auditor")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg['role']): st.markdown(msg['content'])

    if prompt := st.chat_input("Ask about invoices..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                hist = [f"{m['role']}: {m['content']}" for m in st.session_state.messages]
                res = rag_app.invoke({"question": prompt, "chat_history": hist})
                ans = res.get("answer", "No info.")
                score = res.get("reflection_score", {})
                
                final = f"{ans}\n\n*Confidence: {int(score.get('score', 0)*100)}%*" if score.get("is_safe") else f"⚠️ Uncertain.\nReason: {score.get('reason')}"
                st.markdown(final)
                st.session_state.messages.append({"role": "assistant", "content": final})
            except Exception as e: st.error(f"AI Error: {e}")