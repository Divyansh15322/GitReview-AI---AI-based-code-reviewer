import json
from typing import Dict, Any, List
from backend.app.agents.state import ReviewState
from backend.app.agents.utils import get_llm, clean_json_string, query_rag_for_diff, generate_mock_comments
from backend.app.core.config import settings

SECURITY_AGENT_PROMPT = """You are an elite Security Analysis Agent specializing in application security and DevSecOps.
Your goal is to inspect code changes (pull request diffs) and find security risks, vulnerabilities (OWASP Top 10), hardcoded API keys, tokens, SQL injections, XSS, CSRF, insecure cryptographic practices, input sanitization issues, and leakage of sensitive data in logs.

You are reviewing file: `{file_path}`

{rag_context}

Here is the parsed pull request diff containing the added/modified lines (prefixed with line number):
```
{diff_content}
```

Instructions:
1. Examine ONLY the lines modified in the diff.
2. Identify code segments that present a high security risk.
3. For each issue found, create an object matching this JSON structure:
{{
    "file_path": "{file_path}",
    "line_number": <new_line_number_where_issue_resides>,
    "diff_hunk": "<exact changed code block from diff surrounding the issue>",
    "category": "security",
    "severity": "critical" or "warning",
    "title": "<Short, descriptive title of the security vulnerability>",
    "body": "<Detailed explanation of the security vulnerability, exploit scenario, and threat model>",
    "suggestion": "<A code suggestion containing replacement code for the lines. Do NOT write full file. Provide a precise drop-in replacement>"
}}

Output your findings STRICTLY as a JSON array of objects.
If you find no security issues, return an empty JSON array: `[]`
Do not include any chat prefix, suffix, or markdown commentary outside of the JSON block.
"""

async def security_analysis_node(state: ReviewState) -> Dict[str, Any]:
    logs = ["🔒 Security Analysis Agent initiated security audit of modified code..."]
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
            mock_findings = generate_mock_comments("security", file_path)
            comments.extend(mock_findings)
            continue
            
        # Query ChromaDB RAG to fetch global codebase files
        rag_context = await query_rag_for_diff(state, file_path, diff_content)
        
        # Build prompt
        prompt = ChatPromptTemplate.from_template(SECURITY_AGENT_PROMPT).format(
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
            logs.append(f"⚠️ Error running Security Agent on {file_path}: {str(e)}")

    logs.append(f"🔒 Security Analysis Agent completed. Identified {len(comments)} vulnerabilities.")
    return {
        "comments": comments,
        "logs": logs
    }
