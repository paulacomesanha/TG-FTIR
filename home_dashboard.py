# tg_ftir_module.py
import json
from dash import html, dcc, Input, Output, State, ctx
import dash_bootstrap_components as dbc

# ---------- Data ----------
with open("assets/descriptions.json", encoding="utf8") as f:
    desc = json.load(f)

FTIR_POINTS = {
    "source":         {"pos": {"bottom": "308.5px", "left": "-92.5px"},  "text": desc["ftir"]["source"]},
    "interferometer": {"pos": {"bottom": "196px", "left": "-92.5px"},    "text": desc["ftir"]["interferometer"]},
    "data":           {"pos": {"bottom": "77px", "left": "149.5px"},     "text": desc["ftir"]["data"]},
    "detector":       {"pos": {"bottom": "217px", "left": "149.5px"},    "text": desc["ftir"]["detector"]},
}
TGA_POINTS = {
    "data1":    {"pos": {"bottom": "239px", "left": "-0.5px"},  "text": desc["tga"]["data"]},
    "thermo":   {"pos": {"bottom": "30px",  "left": "-0.5px"},  "text": desc["tga"]["balance"]},
    "furnace":  {"pos": {"bottom": "89.5px","left": "-0.5px"},  "text": desc["tga"]["furnace"]},
    "tempctrl": {"pos": {"bottom": "117px", "left": "-0.5px"},  "text": desc["tga"]["regulator"]},
}

def build_buttons_row():
    return html.Div(
        id="hero-wrap",
        children=[
            html.Img(src="/assets/tga_ftir.svg", id="hero-img"),
            dbc.Button("FTIR", id="open-ftir", n_clicks=0, className="btn-hero btn btn-primary"),
            dbc.Button("Transfer line", id="open-transfer", n_clicks=0, className="btn-hero btn btn-secondary"),
            dbc.Button("TG", id="open-tga", n_clicks=0, className="btn-hero btn btn-primary"),
        ]
    )

def build_dashboard_body():
    return html.Div("Deprecated in Home. Usa build_buttons_row().")

def build_modals():
    def modal(prefix, title, esquema_img, diagrama_img, points_dict, general_text):
        buttons = [
            html.Button(
                "",
                id=f"{prefix}-btn-{key}",
                n_clicks=0,
                style={"position": "absolute", "cursor": "pointer", **pt["pos"]},
                className="floating-circle"
            )
            for key, pt in points_dict.items()
        ]

        body = html.Div([
            html.Div([
                html.Img(src=f"/assets/{esquema_img}", style={"width": "100%", "maxWidth": "480px"}),
                html.Img(src=f"/assets/{diagrama_img}", style={"width": "100%", "maxWidth": "480px", "marginTop": "20px"}),
                html.Div(buttons, style={"position": "relative"})
            ], className="d-flex flex-column align-items-center"),

            dcc.Store(id=f"{prefix}-current", data="general"),
            html.Hr(),
            html.Div(id=f"{prefix}-info", className="mt-2")
        ])

        return dbc.Modal(
            [
                dbc.ModalHeader([
                    dbc.ModalTitle(title),
                    html.Button(id=f"close-{prefix}", n_clicks=0, className="btn-close", **{"aria-label": "Close"})
                ], close_button=False),
                dbc.ModalBody(body),
            ],
            id=f"modal-{prefix}", size="lg", centered=True,
        )

    return [
        modal("ftir", "FTIR Spectrometer", "esquema_ftir.svg", "diagrama_ftir.svg", FTIR_POINTS, desc["ftir"]["general"]),
        modal("tga", "TG Analyzer", "esquema_tga.svg", "diagrama_tga.svg", TGA_POINTS, desc["tga"]["general"]),
        dbc.Modal([
            dbc.ModalHeader([
                dbc.ModalTitle("Transfer line"),
                html.Button(id="close-transfer", n_clicks=0, className="btn-close", **{"aria-label": "Close"})
            ], close_button=False),
            dbc.ModalBody(html.Div([html.P(desc["transfer"])])),
        ], id="modal-transfer", size="lg", centered=True)
    ]

def register_callbacks(app):
    # Abrir/cerrar modales
    def toggle(prefix):
        @app.callback(
            Output(f"modal-{prefix}", "is_open"),
            [Input(f"open-{prefix}", "n_clicks"), Input(f"close-{prefix}", "n_clicks")],
            State(f"modal-{prefix}", "is_open"),
            prevent_initial_call=False
        )
        def _toggle(open_clicks, close_clicks, is_open):
            # En primera carga, mantén cerrado
            if ctx.triggered_id is None:
                return False
            return not bool(is_open)

    for p in ["ftir", "tga", "transfer"]:
        toggle(p)

    # Texto dentro de cada modal cuando se pulsan puntos
    def reg_info(prefix, points_dict, general_text):
        inputs = [Input(f"{prefix}-btn-{k}", "n_clicks") for k in points_dict]
        @app.callback(
            [Output(f"{prefix}-info", "children"), Output(f"{prefix}-current", "data")],
            inputs,
            State(f"{prefix}-current", "data"),
            prevent_initial_call=False
        )
        def _show_info(*args):
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
            return dcc.Markdown(points_dict[key]["text"]), key

    reg_info("ftir", FTIR_POINTS, desc["ftir"]["general"])
    reg_info("tga", TGA_POINTS, desc["tga"]["general"])
