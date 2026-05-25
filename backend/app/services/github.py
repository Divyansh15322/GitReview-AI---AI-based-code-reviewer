import re
from typing import Dict, List, Any, Optional
import httpx
from backend.app.core.config import settings

class GitHubService:
    def __init__(self, access_token: Optional[str] = None):
        # Fallback to configuring personal access token if OAuth token not supplied
        self.token = access_token or settings.GITHUB_PAT
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def get_pr_info(self, repo_full_name: str, pr_number: int) -> Dict[str, Any]:
        """
        Retrieves general metadata about a pull request from the GitHub API.
        """
        if settings.DEMO_MODE:
            # High-fidelity mock PR metadata for presentations
            return {
                "number": pr_number,
                "title": "Feat: Add premium stripe integration and secure checkout flow",
                "state": "open",
                "html_url": f"https://github.com/{repo_full_name}/pull/{pr_number}",
                "user": {"login": "hackathon-champ"},
                "head": {"sha": "d3b07384d113edec49eaa6238ad5ff00"},
                "base": {"sha": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"},
                "created_at": "2026-05-23T12:00:00Z"
            }

        url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
        """
        Fetches the raw unified diff of a pull request.
        """
        if settings.DEMO_MODE:
            # Returns a realistic mock unified diff for demonstration
            return """diff --git a/services/payment_service.py b/services/payment_service.py
index e69de29..c3a9108 100644
--- a/services/payment_service.py
+++ b/services/payment_service.py
@@ -1,15 +1,28 @@
 import os
-import stripe
+import stripe # Import stripe client
+import logging
 
+logger = logging.getLogger(__name__)
 stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
 
 def process_charge(amount: int, token: str) -> dict:
     try:
-        charge = stripe.Charge.create(
-            amount=amount,
-            currency="usd",
-            source=token,
-            description="Charge for purchase"
-        )
+        # BUG RISK: If token is empty or invalid, stripe raises card error
+        # SECURITY RISK: Printing raw stripe token to log files!
+        print(f"Processing charge for amount: {amount} with token: {token}")
+        
+        if amount <= 0:
+            raise ValueError("Amount must be greater than zero")
+            
+        # PERFORMANCE RISK: Executing stripe call synchronously in async backend
+        charge = stripe.Charge.create(
+            amount=int(amount),
+            currency="usd",
+            source=token,
+            description="Charge for purchase"
+        )
+        return {"success": True, "charge_id": charge.id}
     except stripe.error.CardError as e:
-        return {"success": False, "error": str(e)}
+        body = e.json_body
+        err = body.get('error', {})
+        logger.error(f"Card declined: {err.get('message')}")
+        return {"success": False, "error": err.get('message')}
"""

        headers = self.headers.copy()
        headers["Accept"] = "application/vnd.github.v3.diff"
        url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
        response = await self.client.get(url, headers=headers)
        response.raise_for_status()
        return response.text

    def parse_diff(self, diff_text: str) -> List[Dict[str, Any]]:
        """
        Parses a raw unified diff, extracting file paths and mapping
        specifically added or modified lines and their content.
        
        Returns a list of dictionaries, one per modified file:
        {
            "file_path": "path/to/file.py",
            "hunks": [
                {
                    "header": "@@ -1,15 +1,28 @@",
                    "lines": [
                        {"new_line_no": 5, "content": "import stripe", "type": "added"},
                        ...
                    ]
                }
            ],
            "changed_lines": {5: "import stripe", ...} # Map of new line numbers to added content
        }
        """
        parsed_files = []
        
        # Split diff by file blocks
        file_blocks = re.split(r'^diff --git ', diff_text, flags=re.MULTILINE)
        
        for block in file_blocks:
            if not block.strip():
                continue
                
            lines = block.splitlines()
            file_path = None
            
            # Identify the new file path (from lines starting with +++)
            for line in lines:
                if line.startswith("+++ b/"):
                    file_path = line[6:]
                    break
                    
            if not file_path:
                continue
                
            # Parse hunks
            hunks = []
            current_hunk = None
            new_line_counter = 0
            
            # Map of modified lines: line_number -> line_content
            changed_lines = {}
            
            for line in lines:
                # Catch hunk header: @@ -old_start,old_count +new_start,new_count @@
                hunk_match = re.match(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
                if hunk_match:
                    new_line_counter = int(hunk_match.group(1))
                    current_hunk = {
                        "header": line,
                        "lines": []
                    }
                    hunks.append(current_hunk)
                    continue
                    
                if current_hunk is None:
                    continue
                    
                # Parse modifications within the active hunk
                if line.startswith("+") and not line.startswith("+++"):
                    # This line is added or modified
                    content = line[1:]
                    current_hunk["lines"].append({
                        "new_line_no": new_line_counter,
                        "content": content,
                        "type": "added"
                    })
                    changed_lines[new_line_counter] = content
                    new_line_counter += 1
                elif line.startswith("-") and not line.startswith("---"):
                    # Deleted lines do not exist in the new file, so we do not increment new_line_counter
                    current_hunk["lines"].append({
                        "new_line_no": None,
                        "content": line[1:],
                        "type": "deleted"
                    })
                else:
                    # Context lines
                    current_hunk["lines"].append({
                        "new_line_no": new_line_counter,
                        "content": line[1:] if len(line) > 0 else "",
                        "type": "context"
                    })
                    new_line_counter += 1
            
            if hunks:
                parsed_files.append({
                    "file_path": file_path,
                    "hunks": hunks,
                    "changed_lines": changed_lines
                })
                
        return parsed_files

    async def post_pr_review(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_sha: str,
        comments: List[Dict[str, Any]],
        summary_body: str
    ) -> Dict[str, Any]:
        """
        Submits a full PR review comprising multiple inline draft comments 
        and an overall summary.
        
        Each comment dictionary in `comments` should have:
        - path: str (file path)
        - line: int (the modified line number)
        - body: str (markdown text)
        """
        if settings.DEMO_MODE:
            # Print to stdout and mock response
            print(f"DEMO MODE: Posting PR Review to {repo_full_name} PR #{pr_number}")
            print(f"Comments summary: {len(comments)} comments. Summary body: {summary_body[:100]}...")
            return {"id": 12345, "state": "APPROVED", "body": summary_body}

        if not self.token:
            raise ValueError("GitHub credentials not configured. Please supply a Token/PAT.")

        url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/reviews"
        
        # Structure payload matching GitHub API specs
        # https://docs.github.com/en/rest/pulls/reviews#create-a-review-for-a-pull-request
        payload = {
            "commit_id": commit_sha,
            "event": "COMMENT", # Puts in draft and posts immediately
            "body": summary_body,
            "comments": []
        }
        
        for c in comments:
            # GitHub API expects inline review comments to specify the path, the new line,
            # and the side of the diff (typically 'RIGHT' for additions/modifications).
            payload["comments"].append({
                "path": c["path"],
                "line": c["line"],
                "body": c["body"],
                "side": "RIGHT"
            })

        response = await self.client.post(url, json=payload)
        
        # If posting individual comments fails due to line mismatch (e.g. if the line is not in the diff context),
        # gracefully fallback to posting a single combined review comment at the PR conversation level.
        if response.status_code != 201:
            fallback_payload = {
                "body": f"{summary_body}\n\n### 📝 Detailed AI Comments\n\n" + "\n\n".join(
                    f"**{c['path']}:L{c['line']}**\n{c['body']}" for c in comments
                ),
                "event": "COMMENT"
            }
            fallback_resp = await self.client.post(url, json=fallback_payload)
            fallback_resp.raise_for_status()
            return fallback_resp.json()
            
        return response.json()
