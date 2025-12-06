from rag_agents.rag_llms import rephrase_llm

def rephrase_node(state: dict) -> dict:
    question = state["question"]
    history = state.get("chat_history", [])
    
    if not history: return {"question": question}
    
    prompt = f"""
    You are a Search Query Optimizer.
    Rewrite the "Latest Question" into a standalone question based on the "Chat History".
    If the question is already standalone, return it exactly as is.
    
    Chat History:
    {history}
    
    Latest Question: {question}
    
    Standalone Question:
    """
    new_q = rephrase_llm.invoke(prompt).strip()
    print(f" [RAG] Rephrased: {new_q}")
    return {"question": new_q}