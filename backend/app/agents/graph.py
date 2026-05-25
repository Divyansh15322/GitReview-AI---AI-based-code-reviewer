from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from backend.app.agents.state import ReviewState
from backend.app.agents.bug_agent import bug_detection_node
from backend.app.agents.security_agent import security_analysis_node
from backend.app.agents.perf_agent import performance_analysis_node
from backend.app.agents.clean_agent import clean_code_analysis_node
from backend.app.agents.summarizer import review_synthesis_node

async def initialize_review_node(state: ReviewState) -> Dict[str, Any]:
    """
    Starter node in the graph. Performs initialization logs and sets up parallel fan-out.
    """
    total_files = len(state.get("files", []))
    log_msg = f"🚀 Starting Parallel Multi-Agent Code Review. Isolating diffs across {total_files} modified files..."
    return {
        "logs": [log_msg],
        "comments": []
    }

# Construct the StateGraph workflow
builder = StateGraph(ReviewState)

# Add Node Definitions
builder.add_node("init", initialize_review_node)
builder.add_node("bug_agent", bug_detection_node)
builder.add_node("security_agent", security_analysis_node)
builder.add_node("performance_agent", performance_analysis_node)
builder.add_node("clean_agent", clean_code_analysis_node)
builder.add_node("synthesizer", review_synthesis_node)

# Map Fan-out Entry Routing (Initial node splits into parallel processes)
builder.set_entry_point("init")
builder.add_edge("init", "bug_agent")
builder.add_edge("init", "security_agent")
builder.add_edge("init", "performance_agent")
builder.add_edge("init", "clean_agent")

# Map Fan-in Merging Routing (Parallel outputs consolidate into the Synthesizer)
builder.add_edge("bug_agent", "synthesizer")
builder.add_edge("security_agent", "synthesizer")
builder.add_edge("performance_agent", "synthesizer")
builder.add_edge("clean_agent", "synthesizer")

# Finish Routing
builder.add_edge("synthesizer", END)

# Compile LangGraph App
review_agent_graph = builder.compile()

async def run_code_review_workflow(
    repository_id: int,
    repository_full_name: str,
    pr_number: int,
    commit_sha: str,
    parsed_files: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    High-level entrypoint that runs the compiled LangGraph workflow.
    """
    # Build initial state dictionary
    initial_state = ReviewState(
        repository_id=repository_id,
        repository_full_name=repository_full_name,
        pr_number=pr_number,
        commit_sha=commit_sha,
        files=parsed_files,
        rag_context="",
        comments=[],
        logs=[],
        summary=None,
        score=100,
        bug_count=0,
        security_count=0,
        performance_count=0,
        clean_code_count=0
    )
    
    # Execute the graph asynchronously
    final_state = await review_agent_graph.ainvoke(initial_state)
    return final_state
