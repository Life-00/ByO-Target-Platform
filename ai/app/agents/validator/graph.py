from langgraph.graph import StateGraph, END
from app.agents.validator.state import ValidatorState
from app.agents.validator.nodes import node_ingest, node_cluster, node_synthesize

def build_validator_graph():
    g = StateGraph(ValidatorState)
    
    g.add_node("ingest", node_ingest)
    g.add_node("cluster", node_cluster)
    g.add_node("synthesize", node_synthesize)
    
    g.set_entry_point("ingest")
    
    g.add_edge("ingest", "cluster")
    g.add_edge("cluster", "synthesize")
    g.add_edge("synthesize", END)
    
    return g.compile()
