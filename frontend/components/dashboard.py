import streamlit as st
import plotly.express as px
import pandas as pd
from utils import APIClient

def load_custom_css():
    """Injects high-fidelity glassmorphic card styles into Streamlit."""
    st.markdown("""
    <style>
        .kpi-container {
            display: flex;
            gap: 15px;
            margin-bottom: 25px;
            flex-wrap: wrap;
        }
        .kpi-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 20px;
            flex: 1;
            min-width: 150px;
            text-align: center;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(5px);
            transition: transform 0.2s, border-color 0.2s;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.2);
        }
        .kpi-card h3 {
            font-size: 14px;
            color: #888888;
            margin: 0 0 10px 0;
            font-weight: 500;
        }
        .kpi-card p {
            font-size: 28px;
            font-weight: 700;
            margin: 0;
            color: #ffffff;
        }
        .kpi-card.score p {
            color: #10B981; /* Emerald Green */
        }
        .kpi-card.bug p {
            color: #EF4444; /* Alert Red */
        }
        .kpi-card.security p {
            color: #F59E0B; /* Warning Amber */
        }
        .kpi-card.perf p {
            color: #3B82F6; /* Info Blue */
        }
    </style>
    """, unsafe_allow_html=True)

def render_dashboard():
    load_custom_css()
    st.title("📊 Review Analytics Dashboard")
    st.markdown("Real-time summary of pull request reviews, repository health scores, and issues across active branches.")
    
    client = APIClient()
    analytics = client.fetch_analytics()
    
    if not analytics or analytics.get("total_reviews", 0) == 0:
        # High-fidelity empty onboarding banner
        st.info("👋 Welcome! You haven't connected any repositories or run reviews yet.")
        st.markdown("""
        ### Get Started in 3 Simple Steps:
        1. Go to the **🔌 Connect Repositories** tab on the sidebar.
        2. Onboard any of your public or private repositories.
        3. Trigger a manual review by entering a Pull Request number, or trigger automatically via webhooks!
        """)
        return

    # Destructure analytics
    total_reviews = analytics["total_reviews"]
    avg_score = analytics["avg_score"]
    bugs = analytics["bug_count"]
    security = analytics["security_count"]
    perf = analytics["performance_count"]
    clean = analytics["clean_code_count"]
    weekly_trends = analytics.get("weekly_trends", [])
    top_issues = analytics.get("top_issues", [])

    # Display KPI Cards
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <h3>Total Reviews</h3>
            <p>{total_reviews}</p>
        </div>
        <div class="kpi-card score">
            <h3>Health Score</h3>
            <p>{avg_score}%</p>
        </div>
        <div class="kpi-card bug">
            <h3>Active Bugs</h3>
            <p>{bugs}</p>
        </div>
        <div class="kpi-card security">
            <h3>Security Risks</h3>
            <p>{security}</p>
        </div>
        <div class="kpi-card perf">
            <h3>Perf Bottlenecks</h3>
            <p>{perf}</p>
        </div>
        <div class="kpi-card">
            <h3>Clean Code</h3>
            <p>{clean}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader("📈 Quality Score Trend")
        if weekly_trends:
            df_trend = pd.DataFrame(weekly_trends)
            # Render a beautiful interactive Plotly Line chart
            fig = px.line(
                df_trend, 
                x="date", 
                y="score", 
                title="Historical PR Codebase Quality Score",
                labels={"date": "Review Date", "score": "Health Score (%)"},
                template="plotly_dark",
                markers=True
            )
            # Customizing line gradients and colors
            fig.update_traces(line_color="#10B981", line_width=3, marker=dict(size=8, color="#ffffff"))
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(range=[0, 105])
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Insufficient timeline records to plot score trends. Check back after running multiple reviews.")

    with col2:
        st.subheader("🍕 Issues Distribution")
        # Visual breakdown
        issues_data = {
            "Category": ["Bugs 🕷️", "Security 🔒", "Performance ⚡", "Code Style 🎨"],
            "Count": [bugs, security, perf, clean]
        }
        df_issues = pd.DataFrame(issues_data)
        
        # Don't render pie chart if all counts are 0
        if sum(issues_data["Count"]) > 0:
            fig_pie = px.pie(
                df_issues,
                names="Category",
                values="Count",
                title="Flagged Issues Category Breakdown",
                color_discrete_sequence=["#EF4444", "#F59E0B", "#3B82F6", "#8B5CF6"],
                template="plotly_dark",
                hole=0.4
            )
            fig_pie.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No code issues registered yet! Perfect score codebase.")

    # Hotspot Files
    st.subheader("🔥 Top High-Risk Code Areas")
    if top_issues:
        df_issues = pd.DataFrame(top_issues)
        df_issues.columns = ["File Location", "Category", "Severity Level", "Issue Count"]
        
        # Obfuscate style tags or color cells
        st.dataframe(
            df_issues,
            column_config={
                "File Location": st.column_config.TextColumn(width="medium"),
                "Category": st.column_config.TextColumn(width="small"),
                "Severity Level": st.column_config.TextColumn(width="small"),
                "Issue Count": st.column_config.NumberColumn(width="small")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.success("No recurring high-risk code hotspots found in this workspace!")
