"""Paletas compartidas por la interfaz y las figuras exportadas."""
import re

PALETTES = {
    "Azul": ("#087BCC", "#76BDED", "#B9C9DC"),
    "Vino": ("#A5133D", "#E4B6C2", "#F2F2F2"),
}


def theme_colors(text, palette="Azul"):
    if palette == "Azul":
        return text
    exact = {
        "#087bcc": "#A5133D", "#76bded": "#E4B6C2",
        "#b9c9dc": "#F2F2F2", "#123f70": "#65132D",
    }

    def replace(match):
        color = match[0].lower()
        if color in exact:
            return exact[color]
        red, green, blue = (int(color[i:i + 2], 16) for i in (1, 3, 5))
        if blue <= red or blue <= green:
            return match[0]
        if red >= 200:
            return "#F2F2F2"
        if red >= 150:
            return "#E4B6C2"
        if red >= 70:
            return "#80646D"
        return "#65132D"

    return re.sub(r"#[0-9a-fA-F]{6}\b", replace, text).replace(
        "rgba(8,123,204,.07)", "rgba(165,19,61,.07)")


def theme_figure(fig, palette="Azul"):
    import plotly.graph_objects as go

    def visit(value):
        if isinstance(value, dict):
            return {key: visit(item) for key, item in value.items()}
        if isinstance(value, list):
            return [visit(item) for item in value]
        if isinstance(value, str):
            return theme_colors(value, palette)
        return value

    return go.Figure(visit(fig.to_dict())) if palette != "Azul" else fig
