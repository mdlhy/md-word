"""Diagram rendering for special fenced code blocks.

Supports: matrix, chart, graph, workflow blocks rendered as images.
Requires: matplotlib (optional), networkx (optional for graphs).

Usage:
    from converter.diagram_renderer import is_diagram_language, render_diagram
"""

import logging
import re
from io import BytesIO

logger = logging.getLogger(__name__)

HAS_MATPLOTLIB = False
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    HAS_MATPLOTLIB = True
except ImportError:
    pass

HAS_NETWORKX = False
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    pass

DIAGRAM_LANGUAGES = {"matrix", "chart", "graph", "workflow"}

PALETTE = [
    "#4285F4", "#EA4335", "#FBBC04", "#34A853",
    "#FF6D01", "#46BDC6", "#7B61FF", "#F538A0",
]


def is_diagram_language(language):
    return language.strip().lower() in DIAGRAM_LANGUAGES


def render_diagram(code, language):
    lang = language.strip().lower()
    if lang == "matrix":
        return _render_matrix(code)
    elif lang == "chart":
        return _render_chart(code)
    elif lang == "graph":
        return _render_graph(code)
    elif lang == "workflow":
        return _render_workflow(code)
    return None, None


def _parse_kv(text):
    kv = {}
    for line in text.strip().split("\n"):
        line = line.strip()
        if ":" in line:
            k, v = line.split(":", 1)
            kv[k.strip().lower()] = v.strip()
    return kv


def _render_matrix(code):
    if not HAS_MATPLOTLIB:
        return None, None
    lines = code.strip().split("\n")
    name = ""
    caption = ""
    rows = []
    for line in lines:
        line = line.strip()
        if line.lower().startswith("name:"):
            name = line.split(":", 1)[1].strip()
        elif line.lower().startswith("caption:"):
            caption = line.split(":", 1)[1].strip()
        elif line and not line.lower().startswith("name"):
            parts = line.split()
            try:
                row = [float(x) for x in parts]
                rows.append(row)
            except ValueError:
                continue
    if not rows:
        return None, None
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.set_xlim(-0.5, len(rows[0]) - 0.5)
    ax.set_ylim(-0.5, len(rows) - 0.5)
    ax.set_aspect("equal")
    ax.axis("off")
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            ax.text(j, len(rows) - 1 - i, f"{val:.0f}" if val == int(val) else f"{val:.2f}",
                    ha="center", va="center", fontsize=12)
    y0, y1 = -0.35, len(rows) - 0.65
    left_x, right_x = -0.35, len(rows[0]) - 0.65
    tick = 0.14
    ax.plot([left_x, left_x], [y0, y1], color="black", linewidth=1.6)
    ax.plot([left_x, left_x + tick], [y0, y0], color="black", linewidth=1.6)
    ax.plot([left_x, left_x + tick], [y1, y1], color="black", linewidth=1.6)
    ax.plot([right_x, right_x], [y0, y1], color="black", linewidth=1.6)
    ax.plot([right_x - tick, right_x], [y0, y0], color="black", linewidth=1.6)
    ax.plot([right_x - tick, right_x], [y1, y1], color="black", linewidth=1.6)
    if name:
        ax.set_title(name, fontsize=14, fontweight="bold")
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue(), caption


def _render_chart(code):
    if not HAS_MATPLOTLIB:
        return None, None
    kv = _parse_kv(code)
    chart_type = kv.get("type", "bar")
    title = kv.get("title", "")
    caption = kv.get("caption", "")
    labels = [l.strip() for l in kv.get("labels", "").split(",")]
    values_key = [k for k in kv.keys() if k not in ("type", "title", "labels", "caption")]
    if not values_key or not labels:
        return None, None
    values = [float(v.strip()) for v in kv[values_key[0]].split(",")]
    if len(values) != len(labels):
        return None, None
    fig, ax = plt.subplots(figsize=(6, 4))
    if chart_type == "bar":
        ax.bar(labels, values, color=PALETTE[:len(labels)])
    elif chart_type == "line":
        ax.plot(labels, values, marker="o", color=PALETTE[0])
    elif chart_type == "pie":
        ax.pie(values, labels=labels, autopct="%1.1f%%", colors=PALETTE[:len(labels)])
    elif chart_type == "scatter":
        ax.scatter(range(len(values)), values, color=PALETTE[:len(values)])
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels)
    if title:
        ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel(values_key[0])
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue(), caption


def _render_graph(code):
    if not HAS_MATPLOTLIB or not HAS_NETWORKX:
        return None, None
    lines = code.strip().split("\n")
    directed = False
    title = ""
    caption = ""
    edges = []
    for line in lines:
        line = line.strip()
        if line.lower().startswith("directed:"):
            directed = "true" in line.lower()
        elif line.lower().startswith("title:"):
            title = line.split(":", 1)[1].strip()
        elif line.lower().startswith("caption:"):
            caption = line.split(":", 1)[1].strip()
        elif "->" in line:
            parts = line.split("->")
            if len(parts) == 2:
                src = parts[0].strip()
                rest = parts[1].strip()
                if ":" in rest:
                    dst, weight = rest.split(":", 1)
                    edges.append((src.strip(), dst.strip(), weight.strip()))
                else:
                    edges.append((src.strip(), rest, "1"))
    if not edges:
        return None, None
    G = nx.DiGraph() if directed else nx.Graph()
    for src, dst, weight in edges:
        G.add_edge(src, dst, weight=weight)
    fig, ax = plt.subplots(figsize=(6, 4))
    pos = nx.spring_layout(G)
    nx.draw(G, pos, ax=ax, with_labels=True, node_color=PALETTE[0],
            node_size=500, font_size=10, font_weight="bold")
    edge_labels = {(u, v): d["weight"] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax)
    if title:
        ax.set_title(title, fontsize=14, fontweight="bold")
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue(), caption


def _render_workflow(code):
    if not HAS_MATPLOTLIB:
        return None, None
    lines = code.strip().split("\n")
    title = ""
    caption = ""
    steps = []
    for line in lines:
        line = line.strip()
        if line.lower().startswith("title:"):
            title = line.split(":", 1)[1].strip()
        elif line.lower().startswith("caption:"):
            caption = line.split(":", 1)[1].strip()
        elif line:
            steps.append(line)
    if not steps:
        return None, None
    fig, ax = plt.subplots(figsize=(6, max(3, len(steps) * 0.8)))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, len(steps) * 1.5 + 1)
    ax.axis("off")
    box_width = 3
    box_height = 0.6
    for i, step in enumerate(steps):
        y = len(steps) * 1.5 - i * 1.5
        x = 5 - box_width / 2
        if step.startswith("[") and step.endswith("]"):
            color = "#E8EAF6"
            text = step[1:-1]
        elif step.startswith("<") and step.endswith(">"):
            color = "#E3F2FD"
            text = step[1:-1]
        elif step.startswith("(") and step.endswith(")"):
            color = "#E8F5E9"
            text = step[1:-1]
        elif step.startswith("{") and step.endswith("}"):
            color = "#FFF3E0"
            text = step[1:-1]
            diamond = plt.Polygon([(5, y + box_height / 2), (5 + box_width / 2, y),
                                    (5, y - box_height / 2), (5 - box_width / 2, y)],
                                   facecolor=color, edgecolor="black")
            ax.add_patch(diamond)
            ax.text(5, y, text, ha="center", va="center", fontsize=10)
            if i < len(steps) - 1:
                ax.annotate("", xy=(5, y - box_height / 2 - 0.1),
                            xytext=(5, y - 1.5 + box_height / 2 + 0.1),
                            arrowprops=dict(arrowstyle="->", color="black"))
            continue
        else:
            color = "#F5F5F5"
            text = step
        rect = FancyBboxPatch((x, y - box_height / 2), box_width, box_height,
                               boxstyle="round,pad=0.1", facecolor=color, edgecolor="black")
        ax.add_patch(rect)
        ax.text(5, y, text, ha="center", va="center", fontsize=10)
        if i < len(steps) - 1:
            ax.annotate("", xy=(5, y - box_height / 2 - 0.1),
                        xytext=(5, y - 1.5 + box_height / 2 + 0.1),
                        arrowprops=dict(arrowstyle="->", color="black"))
    if title:
        ax.set_title(title, fontsize=14, fontweight="bold")
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue(), caption
