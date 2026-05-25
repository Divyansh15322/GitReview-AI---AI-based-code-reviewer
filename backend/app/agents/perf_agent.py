import json
from typing import Dict, Any, List
from backend.app.agents.state import ReviewState
from backend.app.agents.utils import get_llm, clean_json_string, query_rag_for_diff, generate_mock_comments
from backend.app.core.config import settings
from langchain_core.prompts import ChatPromptTemplate

PERF_AGENT_PROMPT = """You are an expert Performance Optimization Agent specializing in high-throughput systems and database efficiency.
Your goal is to inspect code changes (pull request diffs) and find latency bottlenecks, heavy time/space complexities, redundant operations, resource leaks, blocking network operations inside async code, unindexed/inefficient database queries, and general performance regressions.

You are reviewing file: `{file_path}`

{rag_context}

Here is the parsed pull request diff containing the added/modified lines (prefixed with line number):
```
{diff_content}
```

Instructions:
1. Examine ONLY the lines modified in the diff.
2. Identify code segments that present performance bottlenecks or latency concerns.
3. For each issue found, create an object matching this JSON structure:
{{
    "file_path": "{file_path}",
    "line_number": <new_line_number_where_issue_resides>,
    "diff_hunk": "<exact changed code block from diff surrounding the issue>",
    "category": "performance",
    "severity": "critical" or "warning",
    "title": "<Short, descriptive title of the performance bottleneck>",
    "body": "<Detailed explanation of the performance concern, theoretical latency impact, and why it is inefficient>",
    "suggestion": "<A code suggestion containing replacement code for the lines. Do NOT write full file. Provide a precise drop-in replacement>"
}}

Output your findings STRICTLY as a JSON array of objects.
If you find no performance issues, return an empty JSON array: `[]`
Do not include any chat prefix, suffix, or markdown commentary outside of the JSON block.
"""

async def performance_analysis_node(state: ReviewState) -> Dict[str, Any]:
    logs = ["⚡ Performance Optimization Agent initiated latency audit on modified code..."]
    comments = []
    
    llm = get_llm()
    
    for file in state["files"]:
        file_path = file["file_path"]
        changed_lines = file["changed_lines"]
        
        if not changed_lines:
            continue
            
        # Format the changed lines for the LLM
        diff_content = "\n".join(f"Line {ln}: {code}" for ln, code in sorted(changed_lines.items()))
        
        # Pull mock findings if in Demo Mode
        if settings.DEMO_MODE or llm is None:
            mock_findings = generate_mock_comments("performance", file_path)
            comments.extend(mock_findings)
            continue
            
        # Query ChromaDB RAG to fetch global codebase files
        rag_context = await query_rag_for_diff(state, file_path, diff_content)
        
        # Build prompt
        prompt = ChatPromptTemplate.from_template(PERF_AGENT_PROMPT).format(
            file_path=file_path,
            rag_context=rag_context,
            diff_content=diff_content
        )
        
        try:
            # Query Groq API
            response = await llm.ainvoke(prompt)
            clean_res = clean_json_string(response.content)
            
            if clean_res and clean_res != "[]":
                findings = json.loads(clean_res)
                if isinstance(findings, list):
                    # Validate that comments are mapped to actual changed lines
                    for f in findings:
                        line_no = f.get("line_number")
                        if line_no in changed_lines:
                            comments.append(f)
        except Exception as e:
            logs.append(f"⚠️ Error running Performance Agent on {file_path}: {str(e)}")

    logs.append(f"⚡ Performance Optimization Agent completed. Identified {len(comments)} bottlenecks.")
    return {
        "comments": comments,
        "logs": logs
    }
