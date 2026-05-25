import streamlit as st
from utils import APIClient

def render_repositories():
    st.title("🔌 Connect & Manage Repositories")
    st.markdown("Onboard your codebase repositories onto the platform. Once connected, the agent crawls directory files, split code nodes by syntax structures, and builds vector databases to serve context during PR review runs.")

    client = APIClient()
    
    # 1. Onboard Repository Section
    st.subheader("➕ Connect New Repository")
    col1, col2 = st.columns([2.5, 1])
    
    with col1:
        repo_input = st.text_input(
            "GitHub Repository Name",
            placeholder="e.g., owner-name/repo-name",
            help="Specify public or private repositories. Assure your credentials possess write access permissions if webhook generation is desired."
        )
        
    with col2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        connect_btn = st.button("Connect Repository", use_container_width=True, type="primary")

    if connect_btn:
        if not repo_input or "/" not in repo_input:
            st.error("Invalid repository structure format. Ensure it follows 'owner/repo' (e.g. facebook/react).")
        else:
            with st.spinner(f"Connecting '{repo_input}' and registering webhook triggers..."):
                result = client.connect_repository(repo_input)
                if result:
                    st.success(f"Successfully connected repository: '{repo_input}'!")
                    st.toast("Background ChromaDB codebase split & vector indexing queued!")
                    st.rerun()

    st.markdown("---")

    # 2. Existing Repositories List
    st.subheader("📂 Connected Repositories")
    repos = client.fetch_repositories()
    
    if not repos:
        st.info("No repositories onboarded yet. Supply a GitHub repository name above to connect your first codebase!")
        return

    # Render connected repositories list beautifully
    for idx, repo in enumerate(repos):
        # Card wrapper structure
        with st.container():
            col_meta, col_actions = st.columns([3, 1])
            
            with col_meta:
                st.markdown(f"### 📦 [{repo['full_name']}]({repo['html_url']})")
                
                # Render metadata badges
                webhook_status = "Active Webhook 🟢" if repo.get("webhook_id") else "Manual Trigger Only 🟡"
                rag_status = "Indexed in ChromaDB 🟢" if repo.get("is_indexed") else "Queueing RAG Indexing... 🟡"
                
                st.markdown(f"""
                **Integrations**:
                - Webhook state: `{webhook_status}`
                - Codebase vector index: `{rag_status}`
                - Connected date: `{repo['created_at'][:10]}`
                """)
                
            with col_actions:
                st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
                sync_key = f"sync_{repo['id']}_{idx}"
                
                is_syncing = not repo.get("is_indexed")
                
                sync_btn = st.button(
                    "Re-index Codebase" if not is_syncing else "Indexing in progress...",
                    key=sync_key,
                    disabled=is_syncing,
                    use_container_width=True
                )
                
                if sync_btn:
                    with st.spinner("Rebuilding ChromaDB code vector indexes..."):
                        sync_result = client.sync_repository(repo["id"])
                        if sync_result:
                            st.success("Synchronize task successfully dispatched!")
                            st.toast("Codebase re-indexing initiated.")
                            st.rerun()
            
            st.markdown("<hr style='border: 0.5px solid rgba(255,255,255,0.05); margin: 15px 0;'>", unsafe_allow_html=True)
