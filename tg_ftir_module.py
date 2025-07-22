# tg_ftir_module.py
import json
from dash import html, dcc, Input, Output, State, ctx
import dash_bootstrap_components as dbc

# ---------- Data ----------
with open("assets/descriptions.json", encoding="utf8") as f:
    desc = json.load(f)

FTIR_POINTS = {
    "source":         {"pos": {"bottom": "403px", "left": "173.5px"},  "text": desc["ftir"]["source"]},
    "interferometer": {"pos": {"bottom": "270px", "left": "175px"},    "text": desc["ftir"]["interferometer"]},
    "data":           {"pos": {"bottom": "130px", "left": "455.5px"},  "text": desc["ftir"]["data"]},
    "detector":       {"pos": {"bottom": "295.5px", "left": "455.5px"}, "text": desc["ftir"]["detector"]},
}
TGA_POINTS = {
    "data1":     {"pos": {"bottom": "345px", "left": "281px"},  "text": desc["tga"]["data"]},
    "balance":   {"pos": {"bottom": "72px",  "left": "281px"},  "text": desc["tga"]["balance"]},
    "furnace":   {"pos": {"bottom": "175px", "left": "281px"},  "text": desc["tga"]["furnace"]},
    "regulator": {"pos": {"bottom": "207px", "left": "281px"},  "text": desc["tga"]["regulator"]},
}

INFO_BOX_STYLE = {
    "backgroundColor": "rgba(255,255,255,0.95)",
    "padding": "1rem",
    "borderRadius": "8px",
    "margin": "1rem 0 0 0",
    "boxShadow": "0 0 6px rgba(0,0,0,.1)",
}
CIRCLE_BASE = {
    "position": "absolute",
    "width": "1rem",
    "height": "1rem",
    "borderRadius": "50%",
    "cursor": "pointer",
    "zIndex": 5,
}  # colores en assets/style.css (.floating-circle)


# ---------- Helpers UI ----------
def _diagram_with_points(prefix, diagrama_img, points_dict):
    overlay_children = [
        html.Img(src=f"/assets/{diagrama_img}",
                 style={"width": "560px", "display": "block", "margin": "0 auto"})
    ]
    for key, meta in points_dict.items():
        s = {**CIRCLE_BASE, "bottom": meta["pos"]["bottom"], "left": meta["pos"]["left"]}
        overlay_children.append(
            html.Button(id=f"{prefix}-btn-{key}", n_clicks=0,
                        className="floating-circle", style=s, **{"aria-label": key})
        )
    return html.Div(
        overlay_children,
        style={"position": "relative", "width": "560px", "height": "450px", "margin": "1rem auto"},
    )


# ---------- Public builders ----------
def build_dashboard_body():
    """Contenido que irá dentro de la card (sin modales)."""
    buttons_row = dbc.Row(
        style={"position": "relative", "height": "150px", "marginBottom": "2rem"},
        children=[
            dbc.Button("FTIR", id="open-ftir", n_clicks=0, color="primary",
                       style={"position": "absolute", "top": "130%", "left": "20%", "width": "120px"}),
            dbc.Button("Transfer line", id="open-transfer", n_clicks=0, color="secondary",
                       style={"position": "absolute", "top": "15%", "left": "47%", "width": "170px"}),
            dbc.Button("TG", id="open-tga", n_clicks=0, color="primary",
                       style={"position": "absolute", "top": "200%", "left": "75%", "width": "120px"}),
        ]
    )

    ftir_section = dbc.Card(
        [
            html.Img(src="/assets/esquema_ftir.svg",
                     style={"width": "700px", "height": "450px", "display": "block", "margin": "0 auto"}),
            _diagram_with_points("ftir", "diagrama_ftir.svg", FTIR_POINTS),
            html.Div(id="ftir-info", style=INFO_BOX_STYLE, children=dcc.Markdown(desc["ftir"]["general"])),
            dcc.Store(id="ftir-current", data="general"),
        ],
        className="shadow-sm border-0",
        style={"padding": "1rem", "marginBottom": "2rem"}
    )

    tga_section = dbc.Card(
        [
            html.Img(src="/assets/esquema_tga.svg",
                     style={"width": "700px", "height": "450px", "display": "block", "margin": "0 auto"}),
            _diagram_with_points("tga", "diagrama_tga.svg", TGA_POINTS),
            html.Div(id="tga-info", style=INFO_BOX_STYLE, children=dcc.Markdown(desc["tga"]["general"])),
            dcc.Store(id="tga-current", data="general"),
        ],
        className="shadow-sm border-0",
        style={"padding": "1rem"}
    )

    return html.Div([
        buttons_row,
        ftir_section,
        tga_section
    ], style={"overflow": "visible"})


def build_modals():
    """Modales fuera de la card."""
    def modal(prefix, title, esquema, diagrama, points, general):
        overlay = _diagram_with_points(prefix, diagrama, points)
        info_box = html.Div(id=f"{prefix}-info", style=INFO_BOX_STYLE, children=dcc.Markdown(general))
        store = dcc.Store(id=f"{prefix}-current", data="general")
        body = dbc.Card(
            [
                html.Img(src=f"/assets/{esquema}",
                         style={"width": "700px", "height": "450px", "display": "block", "margin": "0 auto"}),
                overlay, info_box, store
            ],
            className="shadow-sm border-0", style={"padding": "1rem"}
        )
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
        modal("ftir", "FTIR Spectrometer", "esquema_ftir.svg", "diagrama_ftir.svg",
              FTIR_POINTS, desc["ftir"]["general"]),
        modal("tga", "TG Analyzer", "esquema_tga.svg", "diagrama_tga.svg",
              TGA_POINTS, desc["tga"]["general"]),
        dbc.Modal([
            dbc.ModalHeader([
                dbc.ModalTitle("Transfer line"),
                html.Button(id="close-transfer", n_clicks=0, className="btn-close", **{"aria-label": "Close"}),
            ], close_button=False),
            dbc.ModalBody(html.Div(dcc.Markdown(desc["transfer"]), id="mark-transfer", style=INFO_BOX_STYLE)),
        ], id="modal-transfer", size="lg", centered=True),
    ]


def register_callbacks(app):
    """Registra callbacks en la app multipágina."""
    # Modales
    def reg_modal(open_id, close_id, modal_id):
        @app.callback(Output(modal_id, "is_open"),
                      [Input(open_id, "n_clicks"), Input(close_id, "n_clicks")],
                      State(modal_id, "is_open"),
                      prevent_initial_call=False)
        def _toggle(n_open, n_close, is_open):
            if ctx.triggered_id is None:
                return is_open
            return not is_open

    reg_modal("open-ftir", "close-ftir", "modal-ftir")
    reg_modal("open-tga", "close-tga", "modal-tga")
    reg_modal("open-transfer", "close-transfer", "modal-transfer")

    # Info boxes
    def reg_info(prefix, points_dict, general_text):
        inputs = [Input(f"{prefix}-btn-{k}", "n_clicks") for k in points_dict]
        @app.callback([Output(f"{prefix}-info", "children"), Output(f"{prefix}-current", "data")],
                      inputs, State(f"{prefix}-current", "data"), prevent_initial_call=False)
        def _show_info(*args):
            current_key = args[-1]; clicks = args[:-1]
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
