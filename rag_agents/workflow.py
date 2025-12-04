from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Any

# Import Nodes
from rag_agents.rephrase_agent import rephrase_node
from rag_agents.retrieval_agent import retrieval_node
from rag_agents.generation_agent import generation_node
from rag_agents.reflection_agent import reflection_node

# Define State
class RagState(TypedDict):
    question: str
    chat_history: List[str]
    context_text: str
    context: List[Any] # Actual documents
    answer: str
    reflection_score: dict
    final_answer: str

def rag_routing(state):
    """
    Decides if the answer is safe to show.
    """
    score = state.get("reflection_score", {})
    if score.get("is_safe", False):
        return "safe"
    else:
        return "unsafe"

def build_rag_graph():
    workflow = StateGraph(RagState)

    # Add Nodes
    workflow.add_node("rephrase", rephrase_node)
    workflow.add_node("retrieve", retrieval_node)
    workflow.add_node("generate", generation_node)
    workflow.add_node("reflect", reflection_node)

    # Build Edge Connections
    workflow.set_entry_point("rephrase")
    workflow.add_edge("rephrase", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "reflect")

    # Conditional Edge based on Reflection Score
    workflow.add_conditional_edges(
        "reflect",
        rag_routing,
        {
            "safe": END,
            "unsafe": END # For now, we just end. Advanced: Loop back to generate.
        }
    )

    return workflow.compile()

# Expose the app
rag_app = build_rag_graph()