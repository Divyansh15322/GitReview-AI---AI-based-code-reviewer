import os
import streamlit as st
import httpx
from typing import Dict, List, Any, Optional

# API Config
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

class APIClient:
    def __init__(self):
        self.base_url = API_BASE
        self.client = httpx.Client(timeout=20.0)

    def get_headers(self) -> Dict[str, str]:
        headers = {}
        # Supply access token if authenticated
        if "access_token" in st.session_state and st.session_state["access_token"]:
            headers["Authorization"] = f"Bearer {st.session_state['access_token']}"
        return headers

    def get_user_id(self) -> Optional[int]:
        return st.session_state.get("user_id")

    def fetch_repositories(self) -> List[Dict[str, Any]]:
        user_id = self.get_user_id()
        if not user_id:
            return []
        try:
            resp = self.client.get(
                f"{self.base_url}/repositories/?user_id={user_id}",
                headers=self.get_headers()
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            st.error(f"Error connecting to backend: {e}")
        return []

    def connect_repository(self, full_name: str) -> Optional[Dict[str, Any]]:
        user_id = self.get_user_id()
        if not user_id:
            return None
        try:
            resp = self.client.post(
                f"{self.base_url}/repositories/connect?user_id={user_id}",
                json={"full_name": full_name},
                headers=self.get_headers()
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                st.error(f"Connection failed: {resp.json().get('detail', 'Unknown error')}")
        except Exception as e:
            st.error(f"Failed to post repository connect: {e}")
        return None

    def sync_repository(self, repo_id: int) -> Optional[Dict[str, Any]]:
        try:
            resp = self.client.post(
                f"{self.base_url}/repositories/{repo_id}/sync",
                headers=self.get_headers()
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            st.error(f"Sync trigger failed: {e}")
        return None

    def fetch_pull_requests(self, repo_id: int) -> List[Dict[str, Any]]:
        # In this demo setup, we fetch pull requests from a custom backend endpoint if available,
        # or list mock PRs. Let's write a flexible backend fetch or trigger manual list
        try:
            # Check PR endpoint
            resp = self.client.get(
                f"{self.base_url}/repositories/{repo_id}",
                headers=self.get_headers()
            )
            if resp.status_code == 200:
                # We can fetch reviews or list registered PRs
                pass
        except Exception:
            pass
        return []

    def trigger_review(self, repo_full_name: str, pr_number: int) -> Optional[Dict[str, Any]]:
        user_id = self.get_user_id()
        try:
            resp = self.client.post(
                f"{self.base_url}/reviews/trigger?user_id={user_id}",
                json={
                    "repository_full_name": repo_full_name,
                    "pr_number": int(pr_number)
                },
                headers=self.get_headers()
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                st.error(f"Trigger review failed: {resp.json().get('detail', 'Unknown error')}")
        except Exception as e:
            st.error(f"Failed to trigger review workflow: {e}")
        return None

    def fetch_reviews_for_pr(self, pr_id: int) -> List[Dict[str, Any]]:
        try:
            resp = self.client.get(
                f"{self.base_url}/reviews/pr/{pr_id}",
                headers=self.get_headers()
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            st.error(f"Failed to fetch PR reviews: {e}")
        return []

    def fetch_review_details(self, review_id: int) -> Optional[Dict[str, Any]]:
        try:
            resp = self.client.get(
                f"{self.base_url}/reviews/{review_id}",
                headers=self.get_headers()
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            st.error(f"Failed to fetch review details: {e}")
        return None

    def fetch_analytics(self) -> Dict[str, Any]:
        user_id = self.get_user_id()
        if not user_id:
            return {}
        try:
            resp = self.client.get(
                f"{self.base_url}/reviews/analytics?user_id={user_id}",
                headers=self.get_headers()
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            st.error(f"Failed to retrieve analytics: {e}")
        return {}

    def query_codebase(self, repo_id: int, query: str) -> List[Dict[str, Any]]:
        try:
            resp = self.client.get(
                f"{self.base_url}/repositories/{repo_id}/search?query={query}",
                headers=self.get_headers()
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            st.error(f"Semantic search query failed: {e}")
        return []

def initialize_session():
    """
    Initializes global session states and captures GitHub OAuth callback redirects.
    """
    # Parse URL parameters (e.g. from GitHub OAuth redirection)
    query_params = st.query_params
    
    if "username" in query_params:
        st.session_state["username"] = query_params["username"]
        st.session_state["access_token"] = query_params["access_token"]
        st.session_state["user_id"] = int(query_params["user_id"])
        # Clean browser address bar
        st.query_params.clear()

    # Establish initial session variables if empty
    if "username" not in st.session_state:
        st.session_state["username"] = None
    if "access_token" not in st.session_state:
        st.session_state["access_token"] = None
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None
