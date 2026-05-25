import streamlit as st
from utils import initialize_session, API_BASE
from components.dashboard import render_dashboard
from components.repositories import render_repositories
from components.reviews import render_reviews
from components.chat import render_chat

# 1. Page Configuration
st.set_page_config(
    page_title="GitReview AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Advanced Premium CSS Injection
st.markdown("""
<style>
    /* Main Background & Fonts */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }
    
    /* Premium Header Title bar */
    .title-banner {
        background: linear-gradient(90deg, #1f2937 0%, #111827 100%);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 20px 25px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 25px;
    }
    
    /* Override standard button alignments */
    div.stButton > button:first-child {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid rgba(240, 246, 252, 0.1);
        border-radius: 6px;
        transition: background-color 0.2s, border-color 0.2s;
    }
    div.stButton > button:first-child:hover {
        background-color: #30363d;
        border-color: #8b949e;
        color: #ffffff;
    }
    
    /* Primary Action Buttons */
    div.stButton > button[type="primary"] {
        background-color: #238636 !important; /* Green */
        color: #ffffff !important;
        border: 1px solid rgba(240, 246, 252, 0.1) !important;
    }
    div.stButton > button[type="primary"]:hover {
        background-color: #2ea043 !important;
    }

    /* Sidebar Profile Box */
    .user-profile {
        display: flex;
        align-items: center;
        gap: 12px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 20px;
    }
    .user-profile img {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        border: 2px solid #238636;
    }
    .user-profile div {
        display: flex;
        flex-direction: column;
    }
    .user-profile span.name {
        font-weight: 600;
        font-size: 14px;
        color: #ffffff;
    }
    .user-profile span.role {
        font-size: 11px;
        color: #888888;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Capture callbacks and initialize session attributes
    initialize_session()
    
    username = st.session_state.get("username")
    avatar_url = "https://avatars.githubusercontent.com/u/583231?v=4" # Default avatar
    
    # 3. Sidebar Panel
    with st.sidebar:
        # App branding header
        st.markdown("""
        <div style="text-align: center; padding: 15px 0 25px 0;">
            <span style="font-size: 32px; font-weight: 800; background: linear-gradient(120deg, #10B981, #3B82F6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">GitReview AI</span>
            <div style="font-size: 12px; color: #888888; margin-top: 5px; font-weight: 500; letter-spacing: 1px;">MULTI-AGENT REVIEWS & RAG</div>
        </div>
        """, unsafe_allow_html=True)
        
        # User session management
        if username:
            st.markdown(f"""
            <div class="user-profile">
                <img src="{avatar_url}" alt="Avatar">
                <div>
                    <span class="name">@{username}</span>
                    <span class="role">GitHub Account Link</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Simple logout button
            if st.button("Disconnect Session", use_container_width=True):
                st.session_state["username"] = None
                st.session_state["access_token"] = None
                st.session_state["user_id"] = None
                st.rerun()
        else:
            # Login action card
            st.markdown("""
            <div style="background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.15); border-radius: 8px; padding: 15px; margin-bottom: 20px; text-align: center;">
                <div style="font-size: 13px; font-weight: 500; color: #f87171; margin-bottom: 10px;">⚠️ AUTHENTICATION REQUIRED</div>
                <div style="font-size: 11px; color: #b91c1c; margin-bottom: 12px; line-height: 1.4;">Sign in to register webhook hooks and post comments back to pull requests.</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Expose the API auth endpoint URL to Streamlit button
            auth_url = f"http://localhost:8000/api/v1/auth/login"
            st.markdown(f'<a href="{auth_url}" target="_self"><button style="width:100%; height:40px; background-color:#24292e; color:white; border:1px solid #444d56; border-radius:6px; cursor:pointer; font-weight:600;">🔐 Connect with GitHub</button></a>', unsafe_allow_html=True)
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        st.markdown("---")
        
        # Navigation menus
        menu_choice = st.radio(
            "Navigation Menu",
            options=[
                "📈 Analytics Dashboard",
                "🔌 Connect Repositories",
                "🔍 PR Reviews Console",
                "💬 Codebase Chat (RAG)"
            ]
        )
        
        st.markdown("---")
        # System health info
        st.markdown("""
        <div style="font-size: 10px; color: #555555; text-align: center; font-weight: 500;">
            SYSTEM ACTIVE • VERSION 1.0.0<br>
            LOCAL CHROMADB INSTANTIATED
        </div>
        """, unsafe_allow_html=True)

    # 4. View Rendering Dispatcher
    if menu_choice == "📈 Analytics Dashboard":
        render_dashboard()
    elif menu_choice == "🔌 Connect Repositories":
        render_repositories()
    elif menu_choice == "🔍 PR Reviews Console":
        render_reviews()
    elif menu_choice == "💬 Codebase Chat (RAG)":
        render_chat()

if __name__ == "__main__":
    main()
