import os
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# Use Google Embeddings (Reliable and Free-tier friendly)
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=API_KEY)
DB_PATH = "faiss_index"

def retrieval_node(state):
    question = state["question"]
    print(f" [RAG] Retrieving context for: {question}")
    
    try:
        db = FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
        docs = db.similarity_search(question, k=3)
        context = "\n\n".join([d.page_content for d in docs])
        return {"context_text": context, "context": docs}
    except Exception as e:
        print(f" [RAG] Retrieval Error: {e}")
        return {"context_text": "No documents found.", "context": []}