"""Paletas compartidas por la interfaz y las figuras exportadas."""
import re

PALETTES = {
    "Azul": ("#087BCC", "#76BDED", "#B9C9DC"),
    "Vino": ("#A5133D", "#E4B6C2", "#F2F2F2"),
}


# El primaryColor de .streamlit/config.toml (azul) no se puede cambiar en ejecución; con la
# paleta Vino se recolorean con CSS los controles de Streamlit que lo usan, en todas las pestañas.
VINO_CSS = """<style>
.stApp {--primary-color:#A5133D;}
[data-testid="stBaseButton-primary"] {background-color:#A5133D!important;border-color:#A5133D!important;color:#FFFFFF!important;}
[data-testid="stBaseButton-primary"]:hover {background-color:#8A0F33!important;border-color:#8A0F33!important;}
[data-testid="stBaseButton-primary"]:disabled {background-color:#E4B6C2!important;border-color:#E4B6C2!important;}
[data-testid="stBaseButton-secondary"]:hover, [data-testid="stBaseButton-secondary"]:focus-visible,
[data-testid="stDownloadButton"] button:hover {border-color:#A5133D!important;color:#A5133D!important;}
[data-testid="stMultiSelectTagsContainer"] [data-tag] {background-color:#A5133D!important;color:#FFFFFF!important;}
[data-testid="stTab"] .react-aria-SelectionIndicator {background-color:#A5133D!important;}
[data-testid="stRadioOption"][data-selected="true"] > div:first-of-type > div:first-child {background-color:#A5133D!important;border-color:#A5133D!important;}
[data-testid="stCheckbox"][data-selected="true"] label > div:nth-child(2) {background-color:#A5133D!important;border-color:#A5133D!important;}
[data-testid="stSlider"] [style*="touch-action"] > div:first-child {filter:hue-rotate(140deg) saturate(1.25) brightness(.7);}
[data-testid="stSlider"] [style*="translate(-50%, -50%)"] {background-color:#A5133D!important;}
[data-testid="stSliderThumbValue"], [data-testid="stSliderThumbValue"] p {color:#A5133D!important;}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) {background-color:#F8E9EE!important;}
[data-testid="stAlertContentInfo"], [data-testid="stAlertContentInfo"] p,
[data-testid="stAlertContentInfo"] li {color:#65132D!important;}
[data-baseweb="tab-highlight"] {background-color:#A5133D!important;}
[data-testid="stTabs"] [role="tab"][aria-selected="true"], [data-testid="stTabs"] [role="tab"][aria-selected="true"] p {color:#A5133D!important;}
[data-testid="stTabs"] [role="tab"]:hover p {color:#A5133D!important;}
[data-baseweb="select"] > div:focus-within, [data-baseweb="input"]:focus-within,
[data-baseweb="textarea"]:focus-within {border-color:#A5133D!important;}


[data-testid="stMarkdownContainer"] a {color:#A5133D;}
[data-testid="stNavigation"] a[aria-current="page"], header a[aria-current="page"] {color:#A5133D!important;}
</style>"""


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
