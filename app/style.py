"""Shared styling for all pages."""

CHAT_CSS = """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 5rem;
    }

    /* Chat message styling */
    .stChatMessage {
        border-radius: 12px;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
    }

    /* Metric cards */
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .metric-card h4 {
        margin: 0;
        color: #64748b;
        font-size: 12px;
        text-transform: uppercase;
    }
    .metric-card p {
        margin: 4px 0 0 0;
        font-size: 24px;
        font-weight: bold;
        color: #1e293b;
    }

    /* Part header */
    .part-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 16px 24px;
        color: white;
        margin-bottom: 16px;
    }
    .part-header h2 {
        margin: 0;
        color: white;
        font-size: 1.3rem;
    }
    .part-header p {
        margin: 4px 0 0 0;
        opacity: 0.85;
        font-size: 0.9rem;
    }
</style>
"""


def inject_css():
    """Inject shared CSS into the page."""
    import streamlit as st
    st.markdown(CHAT_CSS, unsafe_allow_html=True)


def part_header(title: str, description: str):
    """Render a styled part header."""
    import streamlit as st
    st.markdown(f"""
    <div class="part-header">
        <h2>{title}</h2>
        <p>{description}</p>
    </div>
    """, unsafe_allow_html=True)


def show_status_badge(label: str, connected: bool):
    """Show a status badge for a service."""
    import streamlit as st
    if connected:
        st.badge(label, icon=":material/check_circle:", color="green")
    else:
        st.badge(label, icon=":material/circle:", color="gray")
