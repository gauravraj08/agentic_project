import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from rag_agents.rag_llms import reflection_llm

def reflection_node(state: dict) -> dict:
    """
    Critiques the generated answer for hallucination and relevance.
    """
    print(" [RAG] Reflector: Grading answer quality...")
    
    answer = state.get("answer", "")
    question = state["question"]
    context = state.get("context_text", "")

    prompt = ChatPromptTemplate.from_template(
        """You are a RAG Quality Auditor.
        1. Check if the ANSWER is grounded in the CONTEXT.
        2. Check if the ANSWER addresses the QUESTION.
        
        QUESTION: {question}
        CONTEXT: {context}
        PROPOSED ANSWER: {answer}
        
        Return a JSON with a score (0.0 to 1.0) and a boolean 'is_safe'.
        JSON FORMAT:
        {{
            "score": 0.9,
            "is_safe": true,
            "reason": "The answer directly cites the invoice total."
        }}
        """
    )
    
    chain = prompt | reflection_llm | StrOutputParser()
    
    try:
        result_str = chain.invoke({
            "question": question, 
            "context": context, 
            "answer": answer
        })
        # Clean markdown if present
        result_str = result_str.replace("```json", "").replace("```", "").strip()
        score_data = json.loads(result_str)
        
        print(f"   - Score: {score_data.get('score')} ({score_data.get('reason')})")
        return {"reflection_score": score_data}
        
    except Exception as e:
        print(f"   - Reflection Error: {e}")
        # Default to safe if scoring fails, but warn
        return {"reflection_score": {"is_safe": True, "score": 0.5}}