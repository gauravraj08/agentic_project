import os
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

def get_llm(temperature=0.0):
    """
    Factory function to return the configured LLM.
    Switches between OpenAI and Gemini based on what keys you have.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    # Priority 1: Use OpenAI if available (Robust for RAG)
    if openai_key:
        return ChatOpenAI(
            model="gpt-4o-mini", # Cost-effective standard
            temperature=temperature,
            api_key=openai_key
        )
    
    # Priority 2: Use Google Gemini
    elif gemini_key:
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=temperature,
            google_api_key=gemini_key
        )
    
    else:
        raise ValueError("CRITICAL: No API keys found in .env for RAG Agents.")

# Initialize standard instances for the agents to import
# 1. The Generator (Answers questions)
rag_llm = get_llm(temperature=0.0)

# 2. The Reflector (Critics the answer - needs to be strict)
reflection_llm = get_llm(temperature=0.0)

# 3. The Rephraser (Chat history context)
rephrase_llm = get_llm(temperature=0.5)

# print(f" [RAG Init] LLMs Initialized using: {rag_llm.model_name or 'Default Model'}")