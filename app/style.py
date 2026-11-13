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
        position: relative;
        background: linear-gradient(120deg, #4f46e5 0%, #7c3aed 55%, #9333ea 100%);
        border-radius: 16px;
        padding: 22px 28px 22px 32px;
        color: white;
        margin-bottom: 22px;
        box-shadow: 0 10px 28px -10px rgba(79, 70, 229, 0.55);
        overflow: hidden;
    }
    /* Accent bar on the left edge */
    .part-header::before {
        content: "";
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 6px;
        background: rgba(255, 255, 255, 0.85);
    }
    /* Subtle decorative glow in the corner */
    .part-header::after {
        content: "";
        position: absolute;
        right: -40px;
        top: -40px;
        width: 160px;
        height: 160px;
        background: radial-gradient(circle, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0) 70%);
        pointer-events: none;
    }
    .part-header .ph-title {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 0;
        color: #ffffff;
        font-size: 1.45rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        line-height: 1.2;
    }
    .part-header .ph-icon {
        font-size: 1.5rem;
        line-height: 1;
    }
    .part-header .ph-desc {
        margin: 8px 0 0 0;
        opacity: 0.92;
        font-size: 0.95rem;
        font-weight: 400;
        max-width: 70ch;
        line-height: 1.45;
    }
    /* Collapse any empty paragraphs Streamlit may inject around the HTML block */
    .part-header p:empty {
        display: none;
        margin: 0;
    }
    .part-header > :last-child {
        margin-bottom: 0;
    }
</style>
"""


def inject_css():
    """Inject shared CSS into the page."""
    import streamlit as st
    st.markdown(CHAT_CSS, unsafe_allow_html=True)


def part_header(title: str, description: str, icon: str = ""):
    """Render a styled part header.

    Args:
        title: Header title.
        description: Short supporting line.
        icon: Optional emoji/glyph shown before the title.
    """
    import html as _html
    import streamlit as st
    icon_html = f'<span class="ph-icon">{_html.escape(icon)}</span>' if icon else ""
    # Emit as a single line with no leading indentation. Streamlit's markdown
    # parser otherwise treats indented/multi-line HTML as code blocks or wraps
    # stray newlines in empty <p> tags, which adds phantom vertical space.
    html = (
        f'<div class="part-header">'
        f'<h2 class="ph-title">{icon_html}<span>{_html.escape(title)}</span></h2>'
        f'<p class="ph-desc">{_html.escape(description)}</p>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


DIAGRAM_ICON_PX = 110        # target on-screen icon size
DIAGRAM_NATIVE_ICON_PX = 306  # icon size in the PNGs (100pt @ 220dpi, see demos/diagram_style.py)
DIAGRAM_MAX_WIDTH = 1000      # px; Streamlit clamps to the container if narrower
DIAGRAM_MAX_HEIGHT = 680      # px; keeps tall diagrams from dominating the page


def show_diagram(path: str):
    """Display an architecture diagram so its icons render at a consistent size.

    A fixed width shrinks icons to specks in long diagrams and blows them up in
    small ones. Scaling to a target icon size (capped by max width/height) keeps
    every diagram equally legible. The full-resolution PNG is still served, so
    it stays crisp on HiDPI screens.
    """
    import streamlit as st
    try:
        from PIL import Image
        with Image.open(path) as img:
            w, h = img.size
        scale = min(DIAGRAM_ICON_PX / DIAGRAM_NATIVE_ICON_PX, DIAGRAM_MAX_WIDTH / w, DIAGRAM_MAX_HEIGHT / h)
        width = int(w * scale)
    except Exception:
        width = DIAGRAM_MAX_WIDTH
    st.image(path, width=width)


def _queue_sample_prompt(target_key: str, prompt: str, state: dict | None):
    """Button callback: apply any required widget state, then queue/load the prompt.

    Runs before the next script run, so it can safely set widget keys.
    """
    import streamlit as st
    for k, v in (state or {}).items():
        st.session_state[k] = v
    st.session_state[target_key] = prompt


def render_sample_prompts(part_key: str, target_key: str | None = None, action_label: str = "▶ Run",
                          note: str | None = None):
    """Render a part's "💡 Prompts" tab from sample_prompts.PROMPTS[part_key].

    Each prompt shows its purpose, the full text in a copyable box, and a button.
    By default the button queues the prompt for the part's chat input (read it with
    take_sample_prompt). Pass target_key to load it into a text widget instead.
    """
    import streamlit as st
    from sample_prompts import PROMPTS

    target = target_key or f"{part_key}_queued_prompt"
    st.caption(note or "Click **▶ Run** to send a prompt to the chat below, or copy it from the box and edit it first.")
    group = None
    for i, item in enumerate(PROMPTS.get(part_key, [])):
        if item.get("group") and item["group"] != group:
            group = item["group"]
            st.markdown(f"##### {group}")
        with st.container(border=True):
            head, action = st.columns([5, 1], vertical_alignment="center")
            head.markdown(f"**{item['title']}**")
            action.button(
                action_label, key=f"{part_key}_sample_{i}", use_container_width=True,
                on_click=_queue_sample_prompt, args=(target, item["prompt"], item.get("state")),
            )
            if item.get("purpose"):
                st.caption(item["purpose"])
            st.code(item["prompt"], language=None, wrap_lines=True)


def take_sample_prompt(part_key: str) -> str | None:
    """Return (and clear) a prompt queued from the part's Prompts tab, if any."""
    import streamlit as st
    return st.session_state.pop(f"{part_key}_queued_prompt", None)


def show_status_badge(label: str, connected: bool):
    """Show a status badge for a service."""
    import streamlit as st
    if connected:
        st.badge(label, icon=":material/check_circle:", color="green")
    else:
        st.badge(label, icon=":material/circle:", color="gray")


def live_services_caption():
    """Render one subtle caption summarizing which AWS services resolved to live
    vs local simulation, plus the region.

    Reads agentcore_utils.get_agentcore_status(). Guarded so any failure degrades
    silently (nothing rendered) rather than breaking the page.
    """
    import streamlit as st
    try:
        import agentcore_utils
        status = agentcore_utils.get_agentcore_status()
        region = status.get("region", "")
        labels = {
            "memory": "Memory",
            "evaluator": "Evaluator",
            "guardrail": "Guardrail",
            "cognito": "Cognito",
            "policy_store": "Policy Store",
            "gateway": "Gateway",
        }
        live = [name for key, name in labels.items() if status.get(key)]
        if live:
            st.caption(f"🟢 Live AWS: {', '.join(live)} · Region {region}")
        else:
            st.caption(f"⚪ Local simulation — no AWS services resolved · Region {region}")
    except Exception:
        pass
