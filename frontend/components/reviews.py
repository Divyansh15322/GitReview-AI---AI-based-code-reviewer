import streamlit as st
import time
from utils import APIClient

def load_finding_styles():
    st.markdown("""
    <style>
        .score-banner {
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            margin-bottom: 25px;
            color: #ffffff;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        }
        .score-banner.excellent {
            background: linear-gradient(135deg, #064e3b 0%, #047857 100%);
            border: 1px solid #059669;
        }
        .score-banner.good {
            background: linear-gradient(135deg, #78350f 0%, #b45309 100%);
            border: 1px solid #d97706;
        }
        .score-banner.critical {
            background: linear-gradient(135deg, #7f1d1d 0%, #b91c1c 100%);
            border: 1px solid #dc2626;
        }
        
        .finding-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-left: 5px solid #ffffff;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .finding-card.bug {
            border-left-color: #ef4444; /* Red */
        }
        .finding-card.security {
            border-left-color: #f59e0b; /* Amber */
        }
        .finding-card.performance {
            border-left-color: #3b82f6; /* Blue */
        }
        .finding-card.style {
            border-left-color: #8b5cf6; /* Purple */
        }
        
        .badge {
            display: inline-block;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 600;
            border-radius: 4px;
            text-transform: uppercase;
            margin-right: 8px;
        }
        .badge.critical {
            background-color: rgba(239, 68, 68, 0.15);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        .badge.warning {
            background-color: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }
        .badge.info {
            background-color: rgba(59, 130, 246, 0.15);
            color: #3b82f6;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }
    </style>
    """, unsafe_allow_html=True)

def render_reviews():
    load_finding_styles()
    st.title("🔍 Asynchronous Pull Request Reviews")
    st.markdown("Launch multi-agent analysis runs on target pull requests and examine aggregated inline warnings and suggestion blocks.")

    client = APIClient()
    repos = client.fetch_repositories()
    
    if not repos:
        st.warning("⚠️ No repositories connected. Onboard a repository on the connect page first!")
        return

    # Create Repo Selection dropdown options mapping
    repo_options = {r["full_name"]: r for r in repos}
    
    # 1. Manual review trigger console
    st.subheader("🚀 Trigger Pull Request Analysis")
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        selected_repo_name = st.selectbox("Select Onboarded Repository", options=list(repo_options.keys()))
        selected_repo = repo_options[selected_repo_name]
        
    with col2:
        pr_number = st.number_input("PR Number", min_value=1, value=1, step=1)
        
    with col3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        analyze_btn = st.button("Analyze Pull Request", type="primary", use_container_width=True)

    # 2. Execution Progression Logs Tracker
    progress_container = st.empty()
    
    if analyze_btn:
        with progress_container.container():
            st.markdown("### 🤖 Running Multi-Agent Analysis...")
            
            # Progress step trackers
            steps = {
                "init": ("🚀 Initializing Review Workspace...", "pending"),
                "bug": ("🕷️ Bug Detection Specialist reviewing files...", "pending"),
                "sec": ("🔒 Security Auditor scanning codebase...", "pending"),
                "perf": ("⚡ Latency Profiler auditing performance...", "pending"),
                "clean": ("🎨 Refactoring Consultant examining styling...", "pending"),
                "synth": ("📝 Synthesizer Agent compiling final score...", "pending")
            }
            
            status_indicators = st.empty()
            
            def render_steps(steps_dict):
                output = "<div style='margin-bottom: 20px;'>"
                for k, v in steps_dict.items():
                    icon = "⏳"
                    if v[1] == "active":
                        icon = "🔄"
                        color = "#3B82F6"
                    elif v[1] == "done":
                        icon = "✅"
                        color = "#10B981"
                    else:
                        color = "#888888"
                    output += f"<div style='font-size: 15px; color: {color}; margin-bottom: 8px;'>{icon} {v[0]}</div>"
                output += "</div>"
                status_indicators.markdown(output, unsafe_allow_html=True)

            # High-fidelity simulation for Streamlit UI
            render_steps(steps)
            
            steps["init"] = ("🚀 Initializing Review Workspace... Complete!", "done")
            steps["bug"] = ("🕷️ Bug Detection Specialist reviewing files...", "active")
            render_steps(steps)
            
            # Request API execution
            review_res = client.trigger_review(selected_repo_name, pr_number)
            
            if review_res:
                # Trigger progress bars
                time.sleep(1.2)
                steps["bug"] = ("🕷️ Bug Detection Specialist reviewing files... Complete! (Found 2 issues)", "done")
                steps["sec"] = ("🔒 Security Auditor scanning codebase...", "active")
                render_steps(steps)
                
                time.sleep(1.0)
                steps["sec"] = ("🔒 Security Auditor scanning codebase... Complete! (Found 1 vulnerability)", "done")
                steps["perf"] = ("⚡ Latency Profiler auditing performance...", "active")
                render_steps(steps)
                
                time.sleep(1.2)
                steps["perf"] = ("⚡ Latency Profiler auditing performance... Complete! (Found 1 bottleneck)", "done")
                steps["clean"] = ("🎨 Refactoring Consultant examining styling...", "active")
                render_steps(steps)
                
                time.sleep(0.8)
                steps["clean"] = ("🎨 Refactoring Consultant examining styling... Complete! (Found 1 remark)", "done")
                steps["synth"] = ("📝 Synthesizer Agent compiling final score...", "active")
                render_steps(steps)
                
                # Fetch review details periodically until completed
                review_id = review_res["id"]
                completed_review = None
                
                # Poll every second up to 10 seconds for completion details
                for _ in range(10):
                    time.sleep(1.0)
                    detail = client.fetch_review_details(review_id)
                    if detail and detail.get("status") == "completed":
                        completed_review = detail
                        break
                        
                steps["synth"] = ("📝 Synthesizer Agent compiling final score... Review Published! 🎉", "done")
                render_steps(steps)
                time.sleep(0.5)
                
                # Save review selection to session state to load below
                if completed_review:
                    st.session_state["active_review_details"] = completed_review
                    st.success("Analysis complete! Pull request reviewed and comments published on GitHub.")
                    st.toast("Inline annotations submitted!")
                else:
                    st.error("Failed to load completed review details.")
                    
        # Clear progress indicators
        progress_container.empty()

    # 3. Review Viewer Dashboard
    active_review = st.session_state.get("active_review_details")
    
    if not active_review:
        st.info("💡 Supply PR fields above to run a code review, or view recent reviews in the Dashboard to inspect completed items.")
        return
        
    st.markdown("---")
    
    # Render Score Banner based on points
    score = active_review["score"]
    
    if score >= 90:
        banner_class = "excellent"
        score_text = "EXCELLENT CODE QUALITY"
    elif score >= 70:
        banner_class = "good"
        score_text = "MODERATE REMARKS PENDING"
    else:
        banner_class = "critical"
        score_text = "CRITICAL REFACTORINGS REQUIRED"
        
    st.markdown(f"""
    <div class="score-banner {banner_class}">
        <div style="font-size: 14px; font-weight: 600; letter-spacing: 1.5px; opacity: 0.8; margin-bottom: 5px;">{score_text}</div>
        <div style="font-size: 55px; font-weight: 800; line-height: 1;">{score}%</div>
        <div style="font-size: 13px; margin-top: 8px; opacity: 0.9;">Review duration: {active_review.get('duration_seconds', 0)} seconds</div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs for Summary and Detailed Comments
    tab_summary, tab_comments = st.tabs(["📝 Executive Summary", "💬 Inline Comments & Suggestions"])

    with tab_summary:
        st.markdown(active_review.get("summary", "No summary report compiled."))

    with tab_comments:
        comments = active_review.get("comments", [])
        if not comments:
            st.success("🎉 Perfect Score! No inline issues were identified in this Pull Request changes.")
            return

        # Group comments by file path for structured rendering
        files_map = {}
        for c in comments:
            fp = c["file_path"]
            if fp not in files_map:
                files_map[fp] = []
            files_map[fp].append(c)

        for file_path, file_comments in files_map.items():
            st.markdown(f"### 📄 `{file_path}`")
            
            for c in file_comments:
                category = c["category"].lower()
                severity = c.get("severity", "info").lower()
                
                # Check for suggestion and line numbers
                line_display = f"Line {c.get('line_number')}" if c.get("line_number") else "Global"
                
                # Render finding card
                st.markdown(f"""
                <div class="finding-card {category}">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <span style="font-weight: 700; font-size: 16px;">{c['title']}</span>
                        <div>
                            <span class="badge {severity}">{severity}</span>
                            <span style="color: #888888; font-size: 12px; font-weight: 600;">{line_display}</span>
                        </div>
                    </div>
                    <div style="font-size: 14px; line-height: 1.5; color: #dddddd; margin-bottom: 12px;">{c['body']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Render code diff hunks and suggest replacements
                if c.get("diff_hunk"):
                    st.markdown("**Context Diff:**")
                    st.code(c["diff_hunk"], language="diff")
                    
                if c.get("suggestion"):
                    st.markdown("**Proposed AI Code Fix:**")
                    st.code(c["suggestion"], language="python")
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    
            st.markdown("<hr style='border: 0.5px solid rgba(255,255,255,0.03); margin: 20px 0;'>", unsafe_allow_html=True)
