# pages/home_dashboard.py
# -----------------------------------------------------------------------------
# Home dashboard helpers:
# - Botones del “hero”
# - Modales FTIR/TG/Transfer
# - Callbacks para abrir/cerrar modales y mostrar info contextual
#
# Mejoras:
# - Carga del JSON de descripciones con fallback robusto.
# - Tipado y docstrings para facilitar mantenimiento.
# - Orden estable para los botones (evita depender de dicts).
# - Callbacks defensivos para evitar errores en triggers.
# -----------------------------------------------------------------------------

from __future__ import annotations

import json
from functools import lru_cache
from typing import Dict, List

from dash import html, dcc, Input, Output, State, ctx
import dash_bootstrap_components as dbc

# =============================================================================
# Carga robusta del JSON de descripciones
# =============================================================================
@lru_cache(maxsize=1)
def load_descriptions() -> Dict:
    """
    Carga el JSON de descripciones desde /assets/descriptions.json.
    Si el archivo no existe o no es válido, devuelve un fallback mínimo.
    """
    try:
        with open("assets/descriptions.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "ftir": {
                "general": "FTIR system overview.",
                "source": "IR source description.",
                "interferometer": "Interferometer description.",
                "data": "Data acquisition description.",
                "detector": "Detector description.",
            },
            "tga": {
                "general": "TGA system overview.",
                "data": "TGA data stream description.",
                "balance": "Microbalance description.",
                "furnace": "Furnace description.",
                "regulator": "Temperature regulator description.",
            },
            "transfer": "Transfer line description.",
        }

DESC = load_descriptions()

# =============================================================================
# Definición de puntos clicables (posiciones absolutas + textos)
# =============================================================================
FTIR_KEYS: List[str] = ["source", "interferometer", "data", "detector"]
TGA_KEYS: List[str] = ["data1", "thermo", "furnace", "tempctrl"]

FTIR_POINTS: Dict[str, Dict] = {
    "source": {"pos": {"bottom": "308.5px", "left": "-92.5px"}, "text": DESC["ftir"]["source"]},
    "interferometer": {"pos": {"bottom": "196px", "left": "-92.5px"}, "text": DESC["ftir"]["interferometer"]},
    "data": {"pos": {"bottom": "77px", "left": "149.5px"}, "text": DESC["ftir"]["data"]},
    "detector": {"pos": {"bottom": "217px", "left": "149.5px"}, "text": DESC["ftir"]["detector"]},
}
TGA_POINTS: Dict[str, Dict] = {
    "data1": {"pos": {"bottom": "239px", "left": "-0.5px"}, "text": DESC["tga"]["data"]},
    "thermo": {"pos": {"bottom": "30px", "left": "-0.5px"}, "text": DESC["tga"]["balance"]},
    "furnace": {"pos": {"bottom": "89.5px", "left": "-0.5px"}, "text": DESC["tga"]["furnace"]},
    "tempctrl": {"pos": {"bottom": "117px", "left": "-0.5px"}, "text": DESC["tga"]["regulator"]},
}

# =============================================================================
# Construcción de UI
# =============================================================================
def build_buttons_row() -> html.Div:
    """
    Crea la fila 'hero' con la imagen del sistema TG-FTIR y
    tres botones posicionados encima (FTIR / Transfer line / TG).
    """
    return html.Div(
        id="hero-wrap",
        children=[
            html.Img(src="/assets/tga_ftir.svg", id="hero-img", alt="TG-FTIR diagram"),
            dbc.Button("FTIR", id="open-ftir", n_clicks=0, className="btn-hero btn btn-primary"),
            dbc.Button("Transfer line", id="open-transfer", n_clicks=0, className="btn-hero btn btn-secondary"),
            dbc.Button("TG", id="open-tga", n_clicks=0, className="btn-hero btn btn-primary"),
        ],
    )

def _make_modal(
    prefix: str,
    title: str,
    esquema_img: str,
    diagrama_img: str,
    points_dict: Dict[str, Dict],
    general_text: str,
    point_keys_in_order: List[str],
) -> dbc.Modal:
    """
    Crea un modal con:
      - dos imágenes (esquema y diagrama)
      - botones circulares sobrepuestos (hotspots)
      - un área de texto que cambia al pulsar cada botón
    """
    buttons = [
        html.Button(
            "",
            id=f"{prefix}-btn-{key}",
            n_clicks=0,
            style={"position": "absolute", "cursor": "pointer", **points_dict[key]["pos"]},
            className="floating-circle",
            **{"aria-label": f"{prefix} point: {key}"},
        )
        for key in point_keys_in_order
    ]

    body = html.Div(
        [
            html.Div(
                [
                    html.Img(src=f"/assets/{esquema_img}", style={"width": "100%", "maxWidth": "480px"}, alt=f"{title} - scheme"),
                    html.Img(src=f"/assets/{diagrama_img}", style={"width": "100%", "maxWidth": "480px", "marginTop": "20px"}, alt=f"{title} - diagram"),
                    html.Div(buttons, style={"position": "relative"}),
                ],
                className="d-flex flex-column align-items-center",
            ),
            dcc.Store(id=f"{prefix}-current", data="general"),
            html.Hr(),
            html.Div(id=f"{prefix}-info", className="mt-2"),
        ]
    )

    return dbc.Modal(
        [
            dbc.ModalHeader(
                [
                    dbc.ModalTitle(title),
                    html.Button(id=f"close-{prefix}", n_clicks=0, className="btn-close", **{"aria-label": "Close"}),
                ],
                close_button=False,
            ),
            dbc.ModalBody(body),
        ],
        id=f"modal-{prefix}",
        size="lg",
        centered=True,
    )

def build_modals() -> List[dbc.Modal]:
    """Devuelve la lista de modales (FTIR, TG y Transfer line)."""
    return [
        _make_modal("ftir", "FTIR Spectrometer", "esquema_ftir.svg", "diagrama_ftir.svg", FTIR_POINTS, DESC["ftir"]["general"], FTIR_KEYS),
        _make_modal("tga", "TG Analyzer", "esquema_tga.svg", "diagrama_tga.svg", TGA_POINTS, DESC["tga"]["general"], TGA_KEYS),
        dbc.Modal(
            [
                dbc.ModalHeader(
                    [
                        dbc.ModalTitle("Transfer line"),
                        html.Button(id="close-transfer", n_clicks=0, className="btn-close", **{"aria-label": "Close"}),
                    ],
                    close_button=False,
                ),
                dbc.ModalBody(html.Div([html.P(DESC["transfer"])])),
            ],
            id="modal-transfer",
            size="lg",
            centered=True,
        ),
    ]

# =============================================================================
# Callbacks
# =============================================================================
def register_callbacks(app) -> None:
    """Registra los callbacks de toggle y contenido de modales."""

    # --- Toggle abrir/cerrar modales ---
    def _register_toggle(prefix: str) -> None:
        @app.callback(
            Output(f"modal-{prefix}", "is_open"),
            [Input(f"open-{prefix}", "n_clicks"), Input(f"close-{prefix}", "n_clicks")],
            State(f"modal-{prefix}", "is_open"),
            prevent_initial_call=False,
        )
        def _toggle(open_clicks, close_clicks, is_open):
            if ctx.triggered_id is None:
                return False
            return not bool(is_open)

    for _prefix in ("ftir", "tga", "transfer"):
        _register_toggle(_prefix)

    # --- Actualizar texto dentro de modales FTIR/TGA ---
    def _register_info(prefix: str, points_dict: Dict[str, Dict], general_text: str, keys_order: List[str]) -> None:
        inputs = [Input(f"{prefix}-btn-{k}", "n_clicks") for k in keys_order]

        @app.callback(
            [Output(f"{prefix}-info", "children"), Output(f"{prefix}-current", "data")],
            inputs,
            State(f"{prefix}-current", "data"),
            prevent_initial_call=False,
        )
        def _show_info(*args):
            if not args:
                return dcc.Markdown(general_text), "general"
            current_key = args[-1]
            clicks = args[:-1]
            if not any(clicks):
                return dcc.Markdown(general_text), "general"
            trig = ctx.triggered_id
            if trig is None:
                return dcc.Markdown(general_text), "general"
            key = trig.split(f"{prefix}-btn-")[-1]
            if key == current_key:
                return dcc.Markdown(general_text), "general"
            point = points_dict.get(key)
            text = point["text"] if point and "text" in point else general_text
            return dcc.Markdown(text), key

    _register_info("ftir", FTIR_POINTS, DESC["ftir"]["general"], FTIR_KEYS)
    _register_info("tga", TGA_POINTS, DESC["tga"]["general"], TGA_KEYS)
