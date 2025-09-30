# pages/home.py
# -----------------------------------------------------------------------------
# Página de inicio (Home)
# - Tarjeta introductoria + tarjeta con “hero” (imagen TG-FTIR + botones)
# - Modales (FTIR / TG / Transfer line) provienen de home_dashboard.py
#
# Mejoras:
# - Import robusto de módulo hermano sin __init__.py (funciona con Dash Pages).
# - Comentarios y estilos tal y como los tenías (sin cambios visuales).
# -----------------------------------------------------------------------------

from __future__ import annotations

import dash
from dash import html
import dash_bootstrap_components as dbc

# ---------------------------------------------------------------------------
# Import robusto del módulo hermano (funciona aunque pages/ no sea paquete)
#   1) Si app.py ya lo importó, lo reutilizamos desde sys.modules.
#   2) Si no, lo cargamos por ruta con importlib.util.
# ---------------------------------------------------------------------------
import sys
if "home_dashboard" in sys.modules:
    home_dashboard = sys.modules["home_dashboard"]
else:
    import importlib.util
    from pathlib import Path
    _THIS_DIR = Path(__file__).parent.resolve()
    _module_path = _THIS_DIR / "home_dashboard.py"
    _spec = importlib.util.spec_from_file_location("home_dashboard", _module_path)
    home_dashboard = importlib.util.module_from_spec(_spec)  # type: ignore
    assert _spec and _spec.loader
    _spec.loader.exec_module(home_dashboard)  # type: ignore

build_buttons_row = home_dashboard.build_buttons_row
build_modals = home_dashboard.build_modals

# Registrar la página en el enrutador de Dash Pages
dash.register_page(__name__, path='/', name='Home', order=0)
dash._dash_renderer._set_react_version('18.2.0')
# -----------------------------------------------------------------------------
# Estilos reutilizables
# -----------------------------------------------------------------------------
CARD_STYLE = {
    "maxWidth": "800px",
    "width": "100%",
    "backgroundColor": "rgba(255, 255, 255, 0.95)",
    "backdropFilter": "blur(8px)",
    "-webkit-backdrop-filter": "blur(8px)",
    "borderRadius": "15px",
    "boxShadow": "0 8px 25px rgba(0, 0, 0, 0.15)",
    "padding": "2.5rem",
    "border": "1px solid rgba(0,0,0,0.05)",
    "marginTop": "max(3vh, 1.5rem)",
}

SUBTITLE_STYLE = {
    "fontSize": "1.15rem",
    "color": "#495057",
}

LIST_ITEM_STYLE = {
    "padding": "10px 0",
    "color": "#343a40",
    "fontSize": "1.05rem",
}

# -----------------------------------------------------------------------------
# Layout
# -----------------------------------------------------------------------------
layout = dbc.Container(
    [
        # ===== Sección 1: Intro =====
        html.Section(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H1(
                            "DATA MANAGER",
                            className="display-3 text-center mb-3",
                            style={"fontWeight": "600", "color": "#212529", "letterSpacing": "0.05em"},
                        ),
                        html.P(
                            "Developed for the ease of data managing",
                            className="text-center mb-5",
                            style={"fontSize": "1.35rem", "color": "#5a6268", "fontWeight": "300"},
                        ),
                        html.Hr(
                            style={"maxWidth": "60%", "margin": "0 auto 40px auto", "borderColor": "#ced4da"},
                            **{"aria-hidden": "true"},
                        ),
                        html.Div(
                            [
                                html.P(
                                    "Select an option from the sidebar to begin:",
                                    className="text-center mt-4 mb-3",
                                    style=SUBTITLE_STYLE,
                                ),
                                # Lista sin bullets y centrada
                                html.Ul(
                                    [
                                        html.Li(
                                            "TG-FTIR Analysis: Visualize and interact with coupled thermogravimetric and infrared spectroscopy data.",
                                            style=LIST_ITEM_STYLE,
                                        ),
                                        html.Li(
                                            "TG Comparison: Upload and compare multiple thermogravimetric analysis curves on a single chart.",
                                            style=LIST_ITEM_STYLE,
                                        ),
                                    ],
                                    style={"listStyle": "none", "paddingLeft": 0, "textAlign": "left", "maxWidth": "90%"},
                                    className="mx-auto",
                                    role="list",
                                ),
                            ],
                            className="mt-3",
                        ),
                    ]
                ),
                style=CARD_STYLE,
            ),
            **{"aria-label": "Introduction"},
        ),

        # ===== Sección 2: Hero TG-FTIR + botones =====
        html.Section(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H2(
                            "TG-FTIR SYSTEM",
                            className="text-center mb-3",
                            style={"fontWeight": 600, "fontSize": "2.25rem"},
                        ),
                        # Imagen + botones posicionados
                        build_buttons_row(),
                    ],
                    style={"overflow": "visible"},
                ),
                style={**CARD_STYLE, "marginTop": "2rem", "overflow": "visible"},
            ),
            **{"aria-label": "TG-FTIR system overview"},
        ),

        # ===== Modales (FTIR / TG / Transfer line) =====
        *build_modals(),
    ],
    fluid=True,
    className="mb-4",
)