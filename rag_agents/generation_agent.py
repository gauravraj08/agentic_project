from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from rag_agents.rag_llms import rag_llm

def generation_node(state: dict) -> dict:
    """
    Generates an answer using the retrieved context.
    """
    print(" [RAG] Generator: Drafting answer...")
    
    question = state["question"]
    context = state.get("context_text", "")
    
    if not context:
        return {"answer": "I could not find any relevant information in the processed invoices."}

    prompt = ChatPromptTemplate.from_template(
        """You are an AI Invoice Assistant.
        Always Greet the user if they say hi or hello.
          Use the following context to answer the question.
        
        CONTEXT:
        {context}
        
        QUESTION: 
        {question}
        
        If the answer is not in the context, say "I don't know".
        Keep the answer concise and professional.
        ANSWER:"""
    )
    
    chain = prompt | rag_llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question})
    
    return {"answer": answer}