# A simple script to index text
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
# Re-use the embeddings logic
from rag_agents.retrieval_agent import embeddings, DB_PATH

def index_invoice_text(text: str, metadata: dict):
    print(" [Indexing] Saving invoice text to Vector DB...")
    
    doc = Document(page_content=text, metadata=metadata)
    
    # Check if DB exists to append or create new
    try:
        db = FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
        db.add_documents([doc])
    except:
        db = FAISS.from_documents([doc], embeddings)
        
    db.save_local(DB_PATH)
    print(" [Indexing] Success.")