import os
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

# Determine Embeddings Model based on keys
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

DB_PATH = "faiss_index"

def retrieval_node(state: dict) -> dict:
    """
    Searches the Vector DB for invoice context.
    """
    question = state["question"]
    print(f" [RAG] Retriever: Searching for '{question}'...")
    
    if not os.path.exists(DB_PATH):
        return {"context": [], "error": "No invoices indexed yet."}
    
    try:
        vector_store = FAISS.load_local(
            DB_PATH, 
            embeddings, 
            allow_dangerous_deserialization=True
        )
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke(question)
        
        # Format docs into a string
        context_text = "\n\n".join([d.page_content for d in docs])
        return {"context": docs, "context_text": context_text}
        
    except Exception as e:
        return {"context": [], "error": str(e)}