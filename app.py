# app.py
import socket
import webbrowser
from threading import Timer
from typing import Dict

import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import Dash, Input, Output, State, ctx, dcc, html

from pathlib import Path
import sys
import importlib.util

# ======================================================================
# Permite importar módulos desde ./pages aunque no sea un paquete
# (y fallback por ruta si hiciera falta)
# ======================================================================
PROJECT_ROOT = Path(__file__).parent.resolve()
PAGES_DIR = PROJECT_ROOT / "pages"
if str(PAGES_DIR) not in sys.path:
    sys.path.insert(0, str(PAGES_DIR))

try:
    # Import directo (rápido si sys.path ya sirve)
    from home_dashboard import register_callbacks  # type: ignore
except Exception:
    # Fallback: cargar el módulo por ruta sin __init__.py
    _module_path = PAGES_DIR / "home_dashboard.py"
    _spec = importlib.util.spec_from_file_location("home_dashboard", _module_path)
    home_dashboard = importlib.util.module_from_spec(_spec)  # type: ignore
    assert _spec and _spec.loader
    _spec.loader.exec_module(home_dashboard)  # type: ignore
    register_callbacks = home_dashboard.register_callbacks  # type: ignore

# =========================
# Helper functions
# =========================
def find_free_port() -> int:
    """Devuelve un puerto libre del sistema (bind a 0 → OS elige)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def open_browser(port: int) -> None:
    """Abre el navegador en http://127.0.0.1:<port>/."""
    webbrowser.open_new(f"http://127.0.0.1:{port}/")


# =========================
# App Initialization
# =========================
external_stylesheets = [
    dbc.themes.BOOTSTRAP,
    # Font Awesome para iconos
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
]

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True,  # permite callbacks de páginas registradas
    title="DATA MANAGER",
    update_title=None,  # type: ignore
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server  # para despliegues tipo gunicorn

# =========================
# Sidebar config
# =========================
SIDEBAR_WIDTH_OPEN = "20rem"
SIDEBAR_WIDTH_COLLAPSED = "5.5rem"

SIDEBAR_STYLE_BASE: Dict[str, str] = {
    # fijo a la izquierda y ocupa alto completo
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "height": "100vh",
    "overflowY": "auto",
    "flexShrink": "0",
    "boxSizing": "border-box",
    # look & feel
    "backgroundColor": "#e9ecef",
    "borderRight": "1px solid #dee2e6",
    # animaciones suaves
    "transition": "width .3s ease, padding .3s ease",
}  # type: ignore
SIDEBAR_STYLE_OPENED = {
    **SIDEBAR_STYLE_BASE,
    "width": SIDEBAR_WIDTH_OPEN,
    "padding": "1.5rem 1rem",
}
SIDEBAR_STYLE_COLLAPSED = {
    **SIDEBAR_STYLE_BASE,
    "width": SIDEBAR_WIDTH_COLLAPSED,
    "padding": "1rem 0.25rem",
}


def generate_sidebar_nav_links(is_open: bool) -> dbc.Nav:
    """Crea el bloque de enlaces del sidebar (compacto/extendido)."""
    link_items = [
        {"href": "/", "icon": "fas fa-home", "text": "Home"},
        {
            "href": "/tg-comparison",
            "icon": "fas fa-thermometer-half",
            "text": "Thermogravimetric Analysis",
        },
        {
            "href": "/tg-ftir-analysis",
            "icon": "fas fa-chart-line",
            "text": "Evolved Gas Analysis",
        },
    ]
    nav_links = []
    for item in link_items:
        if is_open:
            nav_links.append(
                dbc.NavLink(
                    [html.I(className=f"{item['icon']} me-3 fa-fw"), html.Span(item["text"])],
                    href=item["href"],
                    active="exact",
                    className="py-2 fs-5",
                )
            )
        else:
            nav_links.append(
                dbc.NavLink(
                    [html.I(className=f"{item['icon']} fa-lg fa-fw")],
                    href=item["href"],
                    active="exact",
                    className="my-3 text-center",
                    style={"padding": "0.5rem 0"},
                )
            )
    return dbc.Nav(nav_links, vertical=True, pills=True)


# =========================
# Layout
# =========================
app.layout = dmc.MantineProvider(
    theme={"colorScheme": "light"},  # type: ignore
    children=html.Div(
        style={
            "display": "flex",
            "flexDirection": "row",
            "width": "100vw",
            "height": "100vh",
            "overflow": "hidden",
            "backgroundColor": "#e9ecef",
        },
        children=[
            dcc.Location(id="url", refresh=False),
            dcc.Store(id="sidebar-is-open", data=True),

            # Sidebar
            html.Div(
                id="sidebar",
                children=[
                    html.Div(
                        [
                            html.Button(
                                html.I(id="sidebar-toggle-icon", className="fas fa-times"),
                                id="btn_sidebar_toggle",
                                className="sidebar-toggle-btn",
                                **{"aria-label": "Toggle menu"},  # type: ignore
                                style={
                                    "position": "absolute",
                                    "top": "10px",
                                    "right": "10px",
                                },
                            ),
                            html.H4(
                                "MENU",
                                id="sidebar-title",
                                className="display-6 text-center mt-2 mb-0",
                                style={
                                    "color": "#343a40",
                                    "fontWeight": "500",
                                    "transition": "opacity .2s ease, font-size .2s ease",
                                },
                            ),
                        ],
                        style={"paddingBottom": "1rem", "minHeight": "60px", "position": "relative"},
                    ),
                    html.Hr(id="sidebar-hr", style={"borderColor": "#adb5bd", "transition": "opacity .2s ease"}),
                    html.Div(id="sidebar-nav-content-div"),
                ],
            ),

            # Contenido de páginas
            html.Div(id="page_content_div", children=dash.page_container),
        ],
    ),
)

# Importante: previene el error "validation_layout None"
app.validation_layout = app.layout

# Callbacks de modales del Home
register_callbacks(app)

# =========================
# Callbacks
# =========================
@app.callback(
    Output("sidebar", "style"),
    Output("sidebar-toggle-icon", "className"),
    Output("sidebar-is-open", "data"),
    Output("sidebar-nav-content-div", "children"),
    Output("sidebar-title", "style"),
    Output("sidebar-hr", "style"),
    Input("btn_sidebar_toggle", "n_clicks"),
    State("sidebar-is-open", "data"),
    prevent_initial_call=False,
)
def manage_sidebar_appearance(n_clicks: int | None, sidebar_is_open_current: bool):
    """Abre/cierra el sidebar y actualiza estilos/íconos/links."""
    new_is_open = sidebar_is_open_current
    if ctx.triggered_id == "btn_sidebar_toggle":
        new_is_open = not sidebar_is_open_current

    if new_is_open:
        return (
            SIDEBAR_STYLE_OPENED,
            "fas fa-times",
            new_is_open,
            generate_sidebar_nav_links(True),
            {
                "color": "#343a40",
                "fontWeight": "500",
                "opacity": 1,
                "fontSize": "1.75rem",
                "transition": "opacity .3s ease .1s, font-size .3s ease",
            },
            {"borderColor": "#adb5bd", "opacity": 1, "transition": "opacity .3s ease .1s"},
        )

    # Colapsado
    return (
        SIDEBAR_STYLE_COLLAPSED,
        "fas fa-bars",
        new_is_open,
        generate_sidebar_nav_links(False),
        {
            "color": "#343a40",
            "fontWeight": "500",
            "opacity": 0,
            "fontSize": "0rem",
            "transition": "opacity .2s ease, font-size .2s ease",
        },
        {"borderColor": "#adb5bd", "opacity": 0, "transition": "opacity .2s ease"},
    )


@app.callback(
    Output("page_content_div", "style"),
    Input("url", "pathname"),
    Input("sidebar-is-open", "data"),
)
def style_page_content_wrapper(pathname: str, sidebar_is_open: bool):
    """Calcula el estilo del wrapper del contenido según la ruta y el ancho del sidebar."""
    margin_left_value = SIDEBAR_WIDTH_OPEN if sidebar_is_open else SIDEBAR_WIDTH_COLLAPSED
    base_content_style = {
        "marginLeft": margin_left_value,
        "flexGrow": 1,
        "height": "100vh",
        "overflowY": "auto",
        "position": "relative",
        "boxSizing": "border-box",
        "transition": "margin-left .3s ease",
        "border": "none",
        "outline": "none",
        "background": "#f8f9fa",
    }
    if pathname == "/":
        return {
            **base_content_style,
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "center",
            "justifyContent": "flex-start",
            "padding": "2rem",
        }
    return {**base_content_style, "padding": "2rem"}


if __name__ == "__main__":
    port = find_free_port()
    Timer(1, open_browser, args=[port]).start()
    app.run(debug=False, use_reloader=False, port=port)
