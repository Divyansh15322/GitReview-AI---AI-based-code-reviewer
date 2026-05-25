from typing import TypedDict, List, Dict, Any, Annotated, Optional
import operator

def append_logs(left: List[str], right: List[str]) -> List[str]:
    """Reducer that appends log messages sequentially."""
    return left + right

def append_comments(left: List[Dict[str, Any]], right: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reducer that merges comment findings collected by multiple parallel review agents."""
    return left + right

class ReviewState(TypedDict):
    # Connection details
    repository_id: int
    repository_full_name: str
    pr_number: int
    commit_sha: str
    
    # Parsed pull request diffs
    # Each entry has: file_path, hunks, changed_lines
    files: List[Dict[str, Any]]
    
    # Context retrieved from ChromaDB RAG
    rag_context: str
    
    # Accumulated findings (appended concurrently by specialist agents via reducer)
    comments: Annotated[List[Dict[str, Any]], append_comments]
    
    # Status progression records
    logs: Annotated[List[str], append_logs]
    
    # Output of the consolidation step
    summary: Optional[str]
    score: int
    bug_count: int
    security_count: int
    performance_count: int
    clean_code_count: int
