from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from rag_agents.rag_llms import rephrase_llm

def rephrase_node(state: dict) -> dict:
    """
    Rewrites the question based on chat history so it makes sense to the retriever.
    """
    question = state["question"]
    chat_history = state.get("chat_history", [])
    
    # If no history, no need to rephrase
    if not chat_history:
        return {"question": question}

    print(" [RAG] Rephraser: Refining query based on history...")

    prompt = ChatPromptTemplate.from_template(
        """Given a chat history and the latest user question which might reference context in the chat history, 
        formulate a standalone question which can be understood without the chat history. 
        Do NOT answer the question, just rewrite it if needed.
        
        Chat History:
        {chat_history}
        
        Latest Question: 
        {question}
        
        Standalone Question:"""
    )
    
    chain = prompt | rephrase_llm | StrOutputParser()
    new_question = chain.invoke({"chat_history": chat_history, "question": question})
    
    print(f"   - Original: {question}")
    print(f"   - Rephrased: {new_question}")
    
    return {"question": new_question}