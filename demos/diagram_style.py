"""Shared visual style for all module architecture diagrams.

Every ``demos/module*/diagrams/generate_all.py`` imports from here so the
diagrams look consistent: compact spacing (icons stay large relative to the
canvas), curved arrows, no title (the app shows its own), colour-matched edge labels,
soft rounded clusters, and crisp 512px icons rendered at high DPI.

AWS service icons come from the official AWS Architecture Icons package in
``aws-icons/`` (SVG), rasterised once to 512px PNGs in ``aws-icons/hires/``.
The ``diagrams`` library's bundled AWS icons are only 256px and look soft at
high DPI, so they are deliberately not used.
"""

from __future__ import annotations

import glob
import html
import os
import shutil
import subprocess

from diagrams import Edge, Node

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_ROOT = os.path.join(REPO_ROOT, "aws-icons")
CUSTOM_ICONS = os.environ.get("MLADAS_ICONS", os.path.join(ICON_ROOT, "custom"))
HIRES_DIR = os.path.join(ICON_ROOT, "hires")
ICON_PX = 512
ICON_PT = 100  # icon cell size in points (~1.4in, the diagrams default)

USER = os.path.join(CUSTOM_ICONS, "user.png")
ROBOT = os.path.join(CUSTOM_ICONS, "robot.png")
TOOL = os.path.join(CUSTOM_ICONS, "tool.png")

# --- Palette (AWS-inspired, high contrast on white) -------------------------
NAVY = "#232F3E"
BLUE = "#2563EB"
GREEN = "#059669"
RED = "#DC2626"
ORANGE = "#EA580C"
PURPLE = "#7C3AED"
SLATE = "#64748B"

COMMON = {
    "show": False,
    "direction": "LR",
    "outformat": "png",
    "graph_attr": {
        "dpi": "220",
        "pad": "0.45",
        "nodesep": "0.75",
        "ranksep": "1.15",
        "splines": "spline",  # smooth Bezier curves that route around nodes/clusters
        "bgcolor": "white",
    },
    "node_attr": {"fontname": "Helvetica Bold", "fontsize": "17", "fontcolor": NAVY},
    "edge_attr": {"fontname": "Helvetica Bold", "fontsize": "15", "penwidth": "2.8", "arrowsize": "1.15"},
}

_CLUSTER_TONES = {
    "blue": ("#EFF6FF", "#93C5FD", "#1D4ED8"),
    "orange": ("#FFF7ED", "#FDBA74", "#C2410C"),
    "green": ("#ECFDF5", "#6EE7B7", "#047857"),
    "purple": ("#F5F3FF", "#C4B5FD", "#6D28D9"),
    "gray": ("#F8FAFC", "#CBD5E1", "#334155"),
}


def group(tone: str = "blue") -> dict:
    """Graph attributes for a soft, rounded cluster in the given tone."""
    fill, border, text = _CLUSTER_TONES[tone]
    return {
        "style": "rounded,filled",
        "bgcolor": fill,
        "pencolor": border,
        "penwidth": "2",
        "fontname": "Helvetica Bold",
        "fontsize": "18",
        "fontcolor": text,
        "labeljust": "c",
        "margin": "22",
    }


def flow(color: str = NAVY, label: str = "", dashed: bool = False) -> Edge:
    """A curved arrow whose label is drawn in the same colour as the line."""
    attrs = {"color": color, "fontcolor": color, "style": "dashed" if dashed else "solid"}
    if label:
        # dot centres the label on the edge; a trailing blank line lifts the
        # text clear of the arrow, and side padding keeps it off the curve.
        attrs["label"] = f"  {label}  \n "
    return Edge(**attrs)


def aws_icon(service: str) -> str:
    """Return a 512px PNG for an official AWS service icon, e.g. ``"Amazon-Cognito"``.

    Rasterised from the official SVG on first use and cached in ``aws-icons/hires/``.
    """
    out = os.path.join(HIRES_DIR, f"{service}.png")
    if os.path.exists(out):
        return out
    matches = glob.glob(os.path.join(ICON_ROOT, "Architecture-Service-Icons_*", "*", "64", f"Arch_{service}_64.svg"))
    if not matches:
        raise FileNotFoundError(f"No official AWS icon found for {service!r}")
    if not shutil.which("rsvg-convert"):
        raise RuntimeError("rsvg-convert is required to rasterise AWS icons (brew install librsvg)")
    os.makedirs(HIRES_DIR, exist_ok=True)
    subprocess.run(["rsvg-convert", "-w", str(ICON_PX), "-h", str(ICON_PX), "-o", out, matches[0]], check=True)
    return out


class IconNode(Node):
    """Icon + caption node built as a graphviz HTML table.

    graphviz's own image placement inside a fixed-size node makes wrapped
    labels collide with the icon and aims arrows at the label. A two-cell
    table (icon cell, caption cell) gives exact, consistent composition, and
    edges attach to the icon cell's port so arrowheads land on the icon.
    """

    _icon = None  # bypass diagrams' own image handling

    def __init__(self, label: str, icon: str):
        caption = "<BR/>".join(html.escape(line) for line in label.split("\n"))
        table = (
            '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3">'
            f'<TR><TD PORT="icon" FIXEDSIZE="TRUE" WIDTH="{ICON_PT}" HEIGHT="{ICON_PT}">'
            f'<IMG SRC="{html.escape(icon)}" SCALE="TRUE"/></TD></TR>'
            f'<TR><TD><FONT FACE="Helvetica Bold" POINT-SIZE="17" COLOR="{NAVY}">{caption}</FONT></TD></TR>'
            "</TABLE>>"
        )
        super().__init__(
            table, shape="plaintext", fixedsize="false", width="0", height="0",
            margin="0", style="solid", penwidth="0",
        )

    @property
    def nodeid(self):
        return f"{self._id}:icon"


def _node(label: str, icon: str) -> IconNode:
    return IconNode(label, icon)


def aws(label: str, service: str) -> IconNode:
    """Diagram node using a high-resolution official AWS service icon."""
    return _node(label, aws_icon(service))


def user(label: str) -> IconNode:
    return _node(label, USER)


def agent(label: str) -> IconNode:
    return _node(label, ROBOT)


def tool(label: str) -> IconNode:
    return _node(label, TOOL)


# Official icon file names used across the modules.
BEDROCK = "Amazon-Bedrock"
AGENTCORE = "Amazon-Bedrock-AgentCore"
COGNITO = "Amazon-Cognito"
VERIFIED_PERMISSIONS = "Amazon-Verified-Permissions"
DYNAMODB = "Amazon-DynamoDB"
PRIVATELINK = "AWS-PrivateLink"
CLOUDWATCH = "Amazon-CloudWatch"
XRAY = "AWS-X-Ray"
SNS = "Amazon-Simple-Notification-Service"
LAMBDA = "AWS-Lambda"
