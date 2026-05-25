from typing import Dict, Any, List
from backend.app.agents.state import ReviewState
from backend.app.agents.utils import get_llm, clean_json_string
from backend.app.core.config import settings
from langchain_core.prompts import ChatPromptTemplate

SUMMARIZER_PROMPT = """You are a highly experienced Software Architect and Code Review Coordinator.
Your task is to take a set of individual inline code review comments produced by specialized agents (Bugs, Security, Performance, Clean Code) and write a professional, high-level pull request review summary.

Here is the pull request metadata:
- **Title**: {pr_title}
- **Number**: #{pr_number}
- **Creator**: @{pr_creator}

Here is a list of all raw findings collected by the review agents:
{raw_comments}

Instructions:
1. Provide a professional Executive Summary of the pull request. Write as a constructive, senior reviewer. Highlight what was done well, and summarize the key architectural issues that need resolution.
2. Outline key items of concern grouped by category (Bugs, Security, Performance, Code Style). Provide actionable next steps.
3. Keep the tone professional, helpful, and concise. Avoid listing every single line-by-line comment here; focus on the high-level themes. Use bullet points and clean markdown.
4. Conclude with a clear recommendation (e.g. "Needs changes before merging" or "Approved with minor remarks").

Write a beautiful, structured markdown report. Do not include any JSON or system text.
"""

def compute_health_score(comments: List[Dict[str, Any]]) -> int:
    """
    Computes a software quality health score from 0-100 based on findings.
    - Start with 100 points
    - Critical issue: -15 points
    - Warning issue: -5 points
    - Info issue: -1 point
    - Floor score at 0
    """
    score = 100
    for comment in comments:
        severity = comment.get("severity", "info").lower()
        if severity == "critical":
            score -= 15
        elif severity == "warning":
            score -= 5
        else:
            score -= 1
    return max(0, score)

async def review_synthesis_node(state: ReviewState) -> Dict[str, Any]:
    logs = ["📝 Synthesizer Agent consolidating reports and compiling executive summary..."]
    comments = state.get("comments", [])
    
    # De-duplicate identical comments (same file and line and title)
    seen_comments = set()
    deduped_comments = []
    for c in comments:
        key = (c.get("file_path"), c.get("line_number"), c.get("title"))
        if key not in seen_comments:
            seen_comments.add(key)
            deduped_comments.append(c)
            
    # Tally metrics
    bug_count = sum(1 for c in deduped_comments if c.get("category") == "bug")
    security_count = sum(1 for c in deduped_comments if c.get("category") == "security")
    performance_count = sum(1 for c in deduped_comments if c.get("category") == "performance")
    clean_code_count = sum(1 for c in deduped_comments if c.get("category") in {"style", "clean_code"})
    
    # Compute score
    score = compute_health_score(deduped_comments)
    
    llm = get_llm()
    
    if settings.DEMO_MODE or llm is None:
        # High-fidelity mock markdown report for presentations
        summary = f"""# 🚀 Code Review Summary: PR #{state['pr_number']}

## 📊 Quality Health Score: **{score}/100**

Excellent structural addition implementing the Stripe payment gateway. However, a few critical bug risks and security vulnerabilities require resolution prior to merge.

---

## 🔍 Key Findings by Specialists

### 🕷️ Bug Detection
- **Critical Risk**: Potential unhandled card exception inside `process_charge` if Stripe rejects tokens. Sanity inputs check missing.
- **Warning**: Minimum charge limitations not checked before invoking APIs (Stripe requires minimum USD cent limits).

### 🔒 Security Audit
- **PCI-DSS Compliance Breach**: Printing the raw plaintext `token` parameter directly to standard stdout logging. Obfuscation of keys is required.

### ⚡ Performance Optimization
- **Blocking API Execution**: `stripe.Charge.create` is invoked as a synchronous blocking request in an async FastAPI routine. This should be dispatched to an executor pool to prevent server thread blocking.

### 🎨 Clean Code & Design
- **Configuration Smell**: Hardcoded `os.getenv` retrieval. Standardize configuration variables by routing variables centrally through `config.py` settings.

---

## 💡 Recommended Next Steps
1. Add input sanitization and obfuscate transaction tokens in logging streams.
2. Wrap external calls inside asynchronous executors to maintain FastAPI concurrency capacity.
3. Handle card decline error statuses explicitly, returning structured user-facing messages.

**Status**: 🛑 **Needs changes before merge**
"""
        logs.append("📝 Synthesizer compiled high-fidelity mock review summary successfully.")
        return {
            "comments": deduped_comments,
            "bug_count": bug_count,
            "security_count": security_count,
            "performance_count": performance_count,
            "clean_code_count": clean_code_count,
            "score": score,
            "summary": summary,
            "logs": logs
        }
        
    # Serialize comments list for prompt
    serialized_comments = ""
    for idx, c in enumerate(deduped_comments, 1):
        serialized_comments += f"{idx}. [{c.get('category').upper()}] File: {c.get('file_path')}:L{c.get('line_number')} - **{c.get('title')}** (Severity: {c.get('severity')})\n   *Finding*: {c.get('body')}\n\n"
        
    if not serialized_comments:
        serialized_comments = "No issues or comments were flagged by any specialist agents!"

    # Compile prompt
    prompt = ChatPromptTemplate.from_template(SUMMARIZER_PROMPT).format(
        pr_title="Add Stripe Payment Integration", # Can pass dynamically from state
        pr_number=state["pr_number"],
        pr_creator="hackathon-champ",
        raw_comments=serialized_comments
    )
    
    try:
        response = await llm.ainvoke(prompt)
        summary = response.content.strip()
    except Exception as e:
        logs.append(f"⚠️ Error compiling AI Summary: {e}")
        # Graceful fallback summary
        summary = f"""# 🚀 Code Review Summary: PR #{state['pr_number']}
        
## 📊 Quality Health Score: **{score}/100**

- 🕷️ Bug Findings: {bug_count}
- 🔒 Security Vulnerabilities: {security_count}
- ⚡ Performance Bottlenecks: {performance_count}
- 🎨 Code Style Remarks: {clean_code_count}

Review ran successfully. Detailed findings are posted as inline annotations on your pull request.
"""

    logs.append("📝 Executive review summary generated successfully.")
    return {
        "comments": deduped_comments,
        "bug_count": bug_count,
        "security_count": security_count,
        "performance_count": performance_count,
        "clean_code_count": clean_code_count,
        "score": score,
        "summary": summary,
        "logs": logs
    }
