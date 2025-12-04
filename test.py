# 1. Index Dummy Data
from agents.indexing_tool import index_invoice_text
dummy_text = "Invoice INV-999. Vendor: Acme Corp. Total: $500. Item: Hammer."
index_invoice_text(dummy_text, {"source": "test_invoice"})

# 2. Run Retrieval Node
from rag_agents.retrieval_agent import retrieval_node
state = {"question": "What is the total amount?"}
state.update(retrieval_node(state))

# 3. Run Generation Node
from rag_agents.generation_agent import generation_node
state.update(generation_node(state))
print(f"\nGenerated Answer: {state['answer']}")

# 4. Run Reflection Node
from rag_agents.reflection_agent import reflection_node
state.update(reflection_node(state))