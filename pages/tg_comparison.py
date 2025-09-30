# pages/tg_comparison.py
from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Dict, List, Tuple

import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from dash import Input, Output, State, ctx, dcc, html
from dash.exceptions import PreventUpdate
from scipy.signal import savgol_filter

dash.register_page(__name__, path="/tg-comparison", name="Thermogravimetric Analysis", order=2)
dash._dash_renderer._set_react_version('18.2.0')

# =========================
# Walkthrough: define aquí tus CSV de ejemplo
# =========================
BASE_DIR = Path(__file__).resolve().parents[1]  # carpeta raíz del proyecto (donde está app.py)
WALKTHROUGH_FILES: List[Dict] = [
    {
        "label": "TG_50CO_50P_R10.csv",
        "path": BASE_DIR / "assets" / "walkthrough" / "TG_50CO_50P_R10.csv",
        "delimiter": ",",
    },
    {
        "label": "TG_80CO-20ES_R10R5_W6.csv",
        "path": BASE_DIR / "assets" / "walkthrough" / "TG_80CO-20ES_R10R5_W6.csv",
        "delimiter": ",",
    },
]

PLOTLY_COLORS = [
    "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
    "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52",
]


# =========================
# Utils
# =========================
def decode_csv_file_content(contents: str) -> io.StringIO:
    """dcc.Upload.contents → CSV StringIO con tolerancia a utf-8 / ISO-8859-1."""
    _, content_string = contents.split(",", 1)
    decoded = base64.b64decode(content_string)
    try:
        return io.StringIO(decoded.decode("utf-8"))
    except UnicodeDecodeError:
        return io.StringIO(decoded.decode("ISO-8859-1"))


def _read_table_like(buf: io.StringIO | bytes | bytearray, filename: str) -> pd.DataFrame:
    """
    Lee un archivo tipo tabla:
      - Si el nombre termina en .xls/.xlsx -> intenta leer Excel.
      - Si no -> CSV con autodetección de separador (',' o ';').
    """
    name = (filename or "").lower()
    if name.endswith((".xls", ".xlsx")):
        # Excel: convertir a BytesIO si no lo es
        if isinstance(buf, io.StringIO):
            data = buf.getvalue().encode("utf-8")
            bio: io.BytesIO = io.BytesIO(data)
        elif isinstance(buf, (bytes, bytearray)):
            bio = io.BytesIO(buf)  # type: ignore[arg-type]
        else:
            # ya es un BytesIO u otra cosa parecida
            bio = io.BytesIO(buf.read())  # type: ignore[attr-defined]
        return pd.read_excel(bio)

    # CSV (usa engine='python' para detectar sep automáticamente)
    if isinstance(buf, io.StringIO):
        return pd.read_csv(buf, sep=None, engine="python")
    # bytes -> decodificar como utf-8/latin
    try:
        return pd.read_csv(io.StringIO(buf.decode("utf-8")), sep=None, engine="python")  # type: ignore[arg-type]
    except Exception:
        return pd.read_csv(io.StringIO(buf.decode("ISO-8859-1")), sep=None, engine="python")  # type: ignore[arg-type]


def _select_tg_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Selecciona columnas TG de forma robusta:
      - Si existen 'Sample Temperature', 'Program Temperature', y 'Mass', las devuelve.
      - Si no, busca por nombres similares.
      - No renombra columnas, solo selecciona.
    """
    cols = df.columns.str.lower()
    selected_cols = []

    # Sample Temperature
    for i, c in enumerate(cols):
        if "sample temperature" in c:
            selected_cols.append(df.columns[i])
            break
    # Program Temperature
    for i, c in enumerate(cols):
        if "program temperature" in c:
            selected_cols.append(df.columns[i])
            break
    # Mass
    for i, c in enumerate(cols):
        if "Unsubtracted Weight" in c or "weight" in c or "tg" in c:
            selected_cols.append(df.columns[i])
            break

    # Si no encuentra, usa las dos primeras columnas como fallback
    if not selected_cols:
        selected_cols = df.columns[:2]

    return df[selected_cols].copy()


def calc_smooth_derivative(
    x: np.ndarray, y: np.ndarray, window_length: int = 21, polyorder: int = 2
) -> Tuple[np.ndarray, np.ndarray]:
    """Suaviza y deriva con Savitzky–Golay asegurando ventana válida e impar."""
    n = len(y)
    window_length = max(3, min(window_length, n - 1))
    if window_length % 2 == 0:
        window_length -= 1
    polyorder = min(polyorder, window_length - 1)
    y_smooth = savgol_filter(y, window_length, polyorder)
    dx = float(np.mean(np.diff(x))) if n > 1 else 1.0
    dy_dx = savgol_filter(y, window_length, polyorder, deriv=1, delta=dx)
    return y_smooth, dy_dx


def sync_vis_dict(data_json: Dict[str, str] | None, vis_dict: Dict[str, bool] | None) -> Dict[str, bool]:
    """Sincroniza el diccionario de visibilidad con los nombres de ficheros presentes."""
    if not data_json:
        return {}
    if not vis_dict:
        return {k: True for k in data_json.keys()}
    return {k: vis_dict.get(k, True) for k in data_json.keys()}

# =========================
# Layout
# =========================
header_bar = html.Div(
    [
        # Refresh
        html.Button(
            html.I(className="fa fa-rotate-right"),
            id="refresh-btn-tgcomp",
            title="Reiniciar página",
            n_clicks=0,
            style={
                "fontSize": "28px",
                "background": "none",
                "border": "none",
                "color": "#333",
                "cursor": "pointer",
                "verticalAlign": "middle",
                "position": "absolute",
                "left": "20px",
                "top": "50%",
                "transform": "translateY(-50%)",
            },
        ),
        # Walkthrough
        html.Button(
            html.I(className="fa-solid fa-book"),
            id="walkthrough-btn",
            title="Walkthrough",
            n_clicks=0,
            style={
                "fontSize": "24px",
                "background": "none",
                "border": "none",
                "color": "#333",
                "cursor": "pointer",
                "verticalAlign": "middle",
                "position": "absolute",
                "left": "60px",
                "top": "50%",
                "transform": "translateY(-50%)",
            },
        ),
        html.H2(
            "Thermogravimetric Analysis",
            className="text-center mb-3",
            style={
                "fontWeight": "bold",
                "color": "#333",
                "margin": "0 auto",
                "textAlign": "center",
                "width": "100%",
            },
        ),
    ],
    style={"position": "relative", "display": "flex", "alignItems": "center", "justifyContent": "center", "height": "60px"},
)

layout = html.Div(
    [
        html.Div(
            [header_bar],
            className="shadow-sm p-3 mb-4 bg-light",
            style={"borderBottom": "3px solid #ddd", "background": "#f8f9fa", "borderRadius": "8px"},
        ),
        dbc.Container(
            [
                dcc.Store(id="multi-tg-data-store", data={}),
                dcc.Store(id="show-graph-cards", data=False),
                dcc.Store(id="tg-legend-visibility", data={}),
                dcc.Store(id="walkthrough-data", data=None),  # datos precargados

                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Div(
                                [
                                    dcc.Upload(
                                        id="upload-multi-tg",
                                        children=html.Div(
                                            [
                                                html.I(
                                                    className="fa fa-upload",
                                                    style={"marginRight": "8px", "fontSize": "22px", "color": "#1976d2"},
                                                ),
                                                html.Span(
                                                    "Arrastra o selecciona archivos TG CSV",
                                                    style={"fontWeight": "bold", "color": "#1976d2"},
                                                ),
                                            ],
                                            className="text-center",
                                        ),
                                        style={
                                            "width": "100%",
                                            "height": "70px",
                                            "lineHeight": "70px",
                                            "borderWidth": "2px",
                                            "borderStyle": "dashed",
                                            "borderColor": "#1976d2",
                                            "borderRadius": "12px",
                                            "textAlign": "center",
                                            "background": "#f4f8fb",
                                            "cursor": "pointer",
                                            "marginBottom": "0px",
                                        },
                                        multiple=True,
                                    ),
                                ],
                                style={"display": "flex", "flexDirection": "column", "gap": "8px"},
                            ),
                            html.Div(id="multi-tg-filenames-display", className="mt-3 text-muted"),
                            html.Div(
                                id="tg-unified-legend",
                                style={"marginTop": "18px", "display": "flex", "flexWrap": "wrap", "gap": "12px", "justifyContent": "center"},
                            ),
                        ]
                    ),
                    className="mb-4 shadow-sm",
                    style={"backgroundColor": "rgba(255,255,255,0.92)", "borderRadius": "18px", "boxShadow": "0 4px 24px rgba(25, 118, 210, 0.07)"},
                ),

                dmc.Divider(variant="solid", m="xl", color="#b0b0b0", size="md"),
                html.Div(id="graph-cards-container"),
            ],
            fluid=True,
            className="mt-4",
        ),
    ]
)

# =========================
# Callbacks
# =========================
@dash.callback(
    Output("walkthrough-data", "data"),
    Input("walkthrough-btn", "n_clicks"),
    prevent_initial_call=True,
)
def load_walkthrough(n_clicks: int | None):
    """Lee los CSV definidos en WALKTHROUGH_FILES y devuelve el dict {filename: json}."""
    if not n_clicks:
        raise PreventUpdate

    loaded: Dict[str, str] = {}
    for spec in WALKTHROUGH_FILES:
        path: Path = spec["path"]
        if not path.exists():
            # no rompemos flujo si falta alguno
            continue
        # Lee con heurística (aunque sean CSV)
        raw = path.read_bytes()
        df = _read_table_like(raw, path.name)

        # Selecciona columnas robustamente
        try:
            df_selected = _select_tg_columns(df)
        except Exception:
            # Fallback mínimo: primeras dos columnas
            df_selected = df.iloc[:, [0, 1]].copy()
            df_selected.columns = ["X_Value", "Mass"]

        loaded[spec["label"]] = df_selected.to_json(orient="split")
    return loaded


@dash.callback(
    Output("multi-tg-data-store", "data"),
    Output("multi-tg-filenames-display", "children"),
    Output("show-graph-cards", "data"),
    Input("upload-multi-tg", "contents"),
    Input("walkthrough-data", "data"),
    State("upload-multi-tg", "filename"),
    State("multi-tg-data-store", "data"),
)
def handle_multi_tg_uploads(list_of_contents, walkthrough_loaded, list_of_names, existing_data_json):
    """
    Maneja carga manual (Upload) y automática (Walkthrough).
    Funde los resultados en el store de curvas disponibles.
    """
    current_data = existing_data_json.copy() if existing_data_json else {}
    trigger = ctx.triggered_id

    # --- Carga manual ---------------------------------------------------------
    if trigger == "upload-multi-tg" and list_of_contents:
        newly_added, errors = [], []
        for c, n in zip(list_of_contents, list_of_names):
            if n in current_data:
                continue
            try:
                file_buf = decode_csv_file_content(c)
                df = _read_table_like(file_buf, n)
                df_selected = _select_tg_columns(df)
                current_data[n] = df_selected.to_json(orient="split")
                newly_added.append(n)
            except Exception as e:  # noqa: BLE001
                errors.append(f"Error en {n}: {e}")

        feedback = []
        if newly_added:
            feedback.append(html.P(f"Procesados: {', '.join(newly_added)}", className="text-success"))
        if errors:
            feedback.append(html.Details([html.Summary("Errores:"), html.Ul([html.Li(x) for x in errors])], className="text-danger"))

        if current_data:
            loaded_files_list = [html.Li(f) for f in current_data.keys()]
            feedback.insert(0, html.P(f"Total archivos: {len(current_data)}"))
            feedback.append(html.Details([html.Summary("Archivos cargados:"), html.Ul(loaded_files_list)]))
            return current_data, feedback, True

        feedback.append(html.P("No hay archivos cargados.", className="text-muted"))
        return {}, feedback, False

    # --- Walkthrough ----------------------------------------------------------
    if trigger == "walkthrough-data" and walkthrough_loaded:
        current_data.update(walkthrough_loaded)
        loaded_files_list = [html.Li(f) for f in current_data.keys()]
        feedback = [
            html.P(f"Total archivos: {len(current_data)}"),
            html.P(f"Procesados (walkthrough): {', '.join(walkthrough_loaded.keys())}", className="text-success"),
            html.Details([html.Summary("Archivos cargados:"), html.Ul(loaded_files_list)]),
        ]
        return current_data, feedback, True

    # Estado sin cambios
    if not current_data:
        return {}, html.P("No hay archivos cargados aún.", className="text-muted"), False
    loaded_files_list = [html.Li(f) for f in current_data.keys()]
    return current_data, html.Div([html.P(f"Total archivos: {len(current_data)}"), html.Details([html.Summary("Archivos cargados:"), html.Ul(loaded_files_list)])]), True


@dash.callback(
    Output("graph-cards-container", "children"),
    Input("show-graph-cards", "data"),
)
def show_graph_cards(show_cards: bool):
    """Muestra las tarjetas de gráficos cuando hay datos cargados."""
    if not show_cards:
        return ""
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dcc.Graph(
                                        id="multi-tg-temp-graph",
                                        style={"height": "350px", "width": "100%"},
                                        config={"editable": True, "edits": {"titleText": False}},
                                    )
                                ]
                            ),
                            className="shadow p-3 mb-4 rounded",
                            style={"backgroundColor": "rgba(255,255,255,0.85)", "minHeight": "420px", "display": "flex", "flexDirection": "column", "justifyContent": "center"},
                        ),
                        width=6,
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dcc.Graph(
                                        id="multi-tg-dtg-graph",
                                        style={"height": "350px", "width": "100%"},
                                        config={"editable": True, "edits": {"titleText": False}},
                                    )
                                ]
                            ),
                            className="shadow p-3 mb-4 rounded",
                            style={"backgroundColor": "rgba(255,255,255,0.85)", "minHeight": "420px", "display": "flex", "flexDirection": "column", "justifyContent": "center"},
                        ),
                        width=6,
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dcc.Graph(
                                        id="multi-tg-comparison-graph",
                                        style={"height": "400px", "width": "100%"},
                                        config={"editable": True, "edits": {"titleText": False}},
                                    )
                                ]
                            ),
                            className="shadow p-3 mb-4 rounded",
                            style={"backgroundColor": "rgba(255,255,255,0.85)", "minHeight": "470px", "display": "flex", "flexDirection": "column", "justifyContent": "center"},
                        ),
                        width=12,
                    )
                ]
            ),
        ]
    )


# --------- Gráfico 1: Programas de temperatura
@dash.callback(
    Output("multi-tg-temp-graph", "figure"),
    Input("multi-tg-data-store", "data"),
    Input("tg-legend-visibility", "data"),
)
def plot_temp_programs(data_json, vis_dict):
    fig = go.Figure()
    vis_dict = sync_vis_dict(data_json, vis_dict)
    if not data_json or not any(vis_dict.values()):
        fig.update_layout(xaxis={"visible": False}, yaxis={"visible": False}, plot_bgcolor="white", paper_bgcolor="white")
        return fig

    for i, (filename, df_json_single) in enumerate(data_json.items()):
        if not vis_dict.get(filename, True):
            continue
        df = pd.read_json(io.StringIO(df_json_single), orient="split")
        # Eje Y: Program Temperature, Eje X: índice (tiempo)
        if "Program Temperature" in df.columns:
            y_data = df["Program Temperature"].astype(float).values
            x_data = np.arange(len(y_data))
        elif "Temperature" in df.columns:
            y_data = df["Temperature"].astype(float).values
            x_data = np.arange(len(y_data))
        else:
            continue
        fig.add_trace(go.Scatter(
            x=x_data, y=y_data, mode='lines',
            name=filename.rsplit('.', 1)[0],
            line=dict(width=2, dash="solid")
        ))

    fig.update_layout(
        xaxis_title="Time (s)",
        yaxis_title="Program Temperature (°C)" if "Program Temperature" in df.columns else "Temperature (°C)",
        margin=dict(l=60, r=20, t=10, b=70),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#e0e0e0"),
        yaxis=dict(showgrid=True, gridcolor="#e0e0e0"),
        showlegend=False,
        font_family="Segoe UI, system-ui"
    )
    return fig


# --------- Gráfico 2: Derivada normalizada
@dash.callback(
    Output("multi-tg-dtg-graph", "figure"),
    Input("multi-tg-data-store", "data"),
    Input("tg-legend-visibility", "data"),
)
def plot_multi_tg_dtg(data_json, vis_dict):
    fig = go.Figure()
    vis_dict = sync_vis_dict(data_json, vis_dict)
    if not data_json or not any(vis_dict.values()):
        fig.update_layout(xaxis={"visible": False}, yaxis={"visible": False}, plot_bgcolor="white", paper_bgcolor="white")
        return fig

    for i, (filename, df_json_single) in enumerate(data_json.items()):
        if not vis_dict.get(filename, True):
            continue
        df = pd.read_json(io.StringIO(df_json_single), orient="split")
        # Eje X: Sample Temperature (preferente), si no, Temperature
        if "Sample Temperature" in df.columns:
            x_data = df["Sample Temperature"].astype(float).values
            x_title = "Sample Temperature (°C)"
        elif "Temperature" in df.columns:
            x_data = df["Temperature"].astype(float).values
            x_title = "Temperature (°C)"
        else:
            continue
        # Busca la columna de masa
        mass_col = None
        for col in df.columns:
            col_lower = col.lower()
            if "unsubtracted weight" in col_lower or "weight" in col_lower or "mass" in col_lower or "tg" in col_lower:
                mass_col = col
                break
        if mass_col is None:
            continue
        y_data = df[mass_col].astype(float).values
        init_mass = y_data[0]
        fin_mass = y_data[-1]
        norm_mass = 100 * (y_data - fin_mass) / (init_mass - fin_mass) if (init_mass - fin_mass) != 0 else np.zeros_like(y_data)
        _, deriv = calc_smooth_derivative(x_data, norm_mass)
        deriv_norm = 100 * (deriv - np.min(deriv)) / (np.max(deriv) - np.min(deriv)) if (np.max(deriv) - np.min(deriv)) != 0 else np.zeros_like(deriv)
        fig.add_trace(go.Scatter(
            x=x_data, y=deriv_norm, mode='lines',
            name=filename.rsplit('.', 1)[0],
            line=dict(width=2, dash="solid")
        ))

    fig.update_layout(
        xaxis_title=x_title,
        yaxis_title="Normalized DTG (%)",
        margin=dict(l=60, r=20, t=10, b=70),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#e0e0e0"),
        yaxis=dict(showgrid=True, gridcolor="#e0e0e0"),
        showlegend=False,
        font_family="Segoe UI, system-ui"
    )
    fig.update_yaxes(range=[0, 100])
    return fig


# --------- Gráfico 3: TG normalizada
@dash.callback(
    Output("multi-tg-comparison-graph", "figure"),
    Input("multi-tg-data-store", "data"),
    Input("tg-legend-visibility", "data"),
)
def plot_multi_tg_comparison(data_json, vis_dict):
    fig = go.Figure()
    vis_dict = sync_vis_dict(data_json, vis_dict)
    if not data_json or not any(vis_dict.values()):
        fig.update_layout(xaxis={"visible": False}, yaxis={"visible": False}, plot_bgcolor="white", paper_bgcolor="white")
        return fig

    for i, (filename, df_json_single) in enumerate(data_json.items()):
        if not vis_dict.get(filename, True):
            continue
        df = pd.read_json(io.StringIO(df_json_single), orient="split")
        # Eje X: Sample Temperature o Temperature
        if "Sample Temperature" in df.columns:
            x_data = df["Sample Temperature"].astype(float).values
            x_title = "Sample Temperature (°C)"
        elif "Temperature" in df.columns:
            x_data = df["Temperature"].astype(float).values
            x_title = "Temperature (°C)"
        else:
            continue
        # Busca la columna de masa
        mass_col = None
        for col in df.columns:
            col_lower = col.lower()
            if "unsubtracted weight" in col_lower or "weight" in col_lower or "mass" in col_lower or "tg" in col_lower:
                mass_col = col
                break
        if mass_col is None:
            continue
        y_data = df[mass_col].astype(float).values
        init_mass = y_data[0]
        fin_mass = y_data[-1]
        norm_mass = 100 * (y_data - fin_mass) / (init_mass - fin_mass) if (init_mass - fin_mass) != 0 else np.zeros_like(y_data)
        fig.add_trace(go.Scatter(
            x=x_data, y=norm_mass, mode='lines',
            name=filename.rsplit('.', 1)[0],
            line=dict(width=2, dash="solid")
        ))

    fig.update_layout(
        xaxis_title="Sample Temperature (°C)" if "Sample Temperature" in df.columns else "Temperature (°C)",
        yaxis_title="Weight loss (%)",
        margin=dict(l=60, r=20, t=10, b=70),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#e0e0e0"),
        yaxis=dict(showgrid=True, gridcolor="#e0e0e0"),
        showlegend=False,
        font_family="Segoe UI, system-ui"
    )
    fig.update_yaxes(range=[0, 100])
    return fig


# --- Refresh (client-side) --- (seguro aunque aún no exista el app)
try:
    _app = dash.get_app()
    if _app is not None:
        _app.clientside_callback(
            """
            function(n_clicks){ if (n_clicks > 0) { window.location.reload(); } return null; }
            """,
            Output("refresh-btn-tgcomp", "n_clicks"),
            Input("refresh-btn-tgcomp", "n_clicks"),
        )
except Exception:
    pass


@dash.callback(
    Output("tg-unified-legend", "children"),
    Input("multi-tg-data-store", "data"),
    Input("tg-legend-visibility", "data"),
)
def update_unified_legend(data_json: Dict[str, str] | None, vis_dict: Dict[str, bool] | None):
    """Crea las badges de la leyenda unificada (con ojito para toggle)."""
    vis_dict = sync_vis_dict(data_json, vis_dict)
    if not data_json:
        return []

    legend = []
    for i, filename in enumerate(data_json.keys()):
        color = PLOTLY_COLORS[i % len(PLOTLY_COLORS)]
        visible = vis_dict.get(filename, True)
        icon = "fa fa-eye" if visible else "fa fa-eye-slash"
        legend.append(
            dmc.Badge(
                [
                    filename.rsplit(".", 1)[0],
                    dmc.ActionIcon(
                        html.I(className=icon, style={"color": "white"}),
                        id={"type": "legend-eye", "index": filename},
                        size="sm",
                        color="gray",
                        variant="subtle",
                        style={
                            "marginLeft": "10px",
                            "verticalAlign": "middle",
                            "background": "transparent"
                        },
                        **{"aria-label": "Toggle visibility"},
                    ),
                ],
                color=color,
                variant="filled" if visible else "outline",
                style={"fontSize": "1em", "padding": "8px 16px", "opacity": 1 if visible else 0.4},
            )
        )
    return legend


@dash.callback(
    Output("tg-legend-visibility", "data"),
    Input("multi-tg-data-store", "data"),
    Input({"type": "legend-eye", "index": dash.ALL}, "n_clicks"),
    State("tg-legend-visibility", "data"),
    prevent_initial_call=False,
)
def update_visibility(data_json, _n_clicks_list, vis_dict):
    """
    Alterna visibilidad por archivo cuando se pulsa un 'ojo' en la leyenda.
    """
    if not data_json:
        return {}

    current_vis = vis_dict.copy() if vis_dict else {}
    synced_vis = {filename: current_vis.get(filename, True) for filename in data_json.keys()}

    # ¿Se ha pulsado un ojo?
    if isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == "legend-eye":
        fname = ctx.triggered_id["index"]
        if fname in synced_vis:
            synced_vis[fname] = not synced_vis[fname]

    return synced_vis




