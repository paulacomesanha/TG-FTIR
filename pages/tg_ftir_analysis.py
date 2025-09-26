# pages/tg_ftir_analysis.py
# -----------------------------------------------------------------------------
# Evolved Gas Analysis (TG-FTIR)
# - Carga TG (CSV), GS (XLSX) y FTIR (CSV)
# - Sincroniza tiempo entre TG/GS y muestra espectro FTIR más cercano
# - Permite "fijar" espectros y compararlos (como en la primera versión funcional)
# - Incluye botón "Walkthrough" para precargar ficheros de ejemplo
# - Chat experto (opcional, igual que antes)
# - ***SIN*** conversión a absorbancia (eliminada por completo)
# -----------------------------------------------------------------------------

from __future__ import annotations

import base64
import io
import os
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from dash import dcc, html, Input, Output, State, ctx
from dash.exceptions import PreventUpdate
from dotenv import load_dotenv
from scipy.signal import savgol_filter

# (opcionales) usados en tu primera versión
from dash import dash_table  # noqa: F401
import dash_daq as daq       # noqa: F401

# ------------------ OpenAI (opcional, como tenías) ------------------
import openai  # type: ignore
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# ------------------ Registro de página ------------------
dash.register_page(__name__, path='/tg-ftir-analysis', name='Evolved Gas Analysis (EGA)', order=1)

# ------------------ Walkthrough: archivos de ejemplo ------------------
BASE_DIR = Path(__file__).resolve().parents[1]
EGA_WALKTHROUGH = {
    # TG CSV (el callback lee con delimiter=',')
    "tg": {
        "label": "TG_50CO_50P_R10.csv",
        "path": BASE_DIR / "assets" / "walkthrough" / "TG_50CO_50P_R10.csv",
        "mime": "text/csv"
    },
    # GS XLSX (se usa read_excel(skiprows=4))
    "gs": {
        "label": "GS_50CO_50P_R10.xlsx",
        "path": BASE_DIR / "assets" / "walkthrough" / "GS_50CO_50P_R10.xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    },
    # FTIR CSV (el callback lo lee con delimiter=';')
    "ftir": {
        "label": "SP_50CO_50P_R10.csv",
        "path": BASE_DIR / "assets" / "walkthrough" / "SP_50CO_50P_R10.csv",
        "mime": "text/csv"
    }
}

def _file_to_contents(path: Path, mime: str) -> str:
    """Convierte un archivo local a la cadena base64 que espera dcc.Upload.contents."""
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def decode_file(contents, file_type='csv'):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    if file_type == 'xlsx':
        return io.BytesIO(decoded)
    elif file_type == 'csv':
        try:
            return io.StringIO(decoded.decode('utf-8'))
        except UnicodeDecodeError:
            return io.StringIO(decoded.decode('ISO-8859-1'))
    else:
        raise ValueError("Unsupported file type")

def calc_smooth_derivative(x, y, window_length=21, polyorder=2):
    if len(y) < 3:
        # seguridad: sin puntos suficientes, devuelve ceros
        return np.asarray(y, dtype=float), np.zeros_like(y, dtype=float)
    if window_length >= len(y):
        window_length = len(y) - 1 if len(y) % 2 == 0 else len(y)
    if window_length < 3:
        window_length = 3
    if window_length % 2 == 0:
        window_length += 1
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    y_smooth = savgol_filter(y, window_length, polyorder)
    delta = float(np.mean(np.diff(x))) if len(x) > 1 else 1.0
    dy_dx = savgol_filter(y, window_length, polyorder, deriv=1, delta=delta)
    return y_smooth, dy_dx

# ------------------ Estado global ------------------
tg = gs = ftir = None
last_ftir_hash = None

# Paleta de colores para fijados (como tenías)
PLOTLY_COLORS = [
    "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
    "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52"
]

# ------------------ Layout ------------------
layout = dmc.MantineProvider(
    theme={"colorScheme": "light"},
    children=html.Div([
        # ======= Header =======
        html.Div([
            html.Div([
                # Refresh
                html.Button(
                    html.I(className="fa fa-rotate-right"),
                    id="refresh-btn",
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
                        "transform": "translateY(-50%)"
                    }
                ),
                # Walkthrough
                html.Button(
                    html.I(className="fa-solid fa-book"),
                    id="walkthrough-btn-ega",
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
                        "transform": "translateY(-50%)"
                    }
                ),
                html.H2(
                    "EGA Data Manager",
                    className="text-center mb-3",
                    style={
                        "fontWeight": "bold",
                        "color": "#333",
                        "margin": "0 auto",
                        "textAlign": "center",
                        "width": "100%"
                    }
                ),
            ], style={
                "position": "relative",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "height": "60px"
            }),
        ], className="shadow-sm p-3 mb-4 bg-light",
        style={"borderBottom": "3px solid #ddd", "background": "#f8f9fa", "borderRadius": "8px"}),

        # ======= Upload cards =======
        dbc.Container([
            dbc.Row([
                # TG
                dbc.Col(html.Div([
                    dbc.Card(
                        dbc.CardBody([
                            html.H4("Upload TG CSV", className="text-center"),
                            dcc.Upload(
                                id='upload-tg',
                                children=html.Div(
                                    ['Select/Drop a TG File'],
                                    className="text-center",
                                    style={"whiteSpace": "nowrap"}
                                ),
                                style={
                                    'width': '100%', 'height': '120px', 'lineHeight': '120px',
                                    'borderWidth': '2px', 'borderStyle': 'solid', 'borderRadius': '10px',
                                    'textAlign': 'center', 'backgroundColor': '#b0c4de', 'color': '#ffffff',
                                    'fontWeight': 'bold', 'cursor': 'pointer'
                                }
                            ),
                            html.Div(id='tg-status', style={
                                "transform": "translateX(-50%)", "zIndex": 5, "marginTop": "8px",
                                "left": "50%", "position": "absolute"
                            }),
                            dmc.Space(h=35),  # espacio vertical de 35px
                            html.Div(id='tg-alert', className="mt-2"),
                        ], style={"position": "relative"}),
                        className="shadow p-4 rounded",
                        style={"position": "relative", "overflow": "hidden"}
                    )
                ]), width=4),

                # GS
                dbc.Col(html.Div([
                    dbc.Card(
                        dbc.CardBody([
                            html.H4("Upload GS XLSX", className="text-center"),
                            dcc.Upload(
                                id='upload-gs',
                                children=html.Div(
                                    ['Select/Drop a GS File'],
                                    className="text-center",
                                    style={"whiteSpace": "nowrap"}
                                ),
                                style={
                                    'width': '100%', 'height': '120px', 'lineHeight': '120px',
                                    'borderWidth': '2px', 'borderStyle': 'solid', 'borderRadius': '10px',
                                    'textAlign': 'center', 'backgroundColor': '#b0c4de', 'color': '#ffffff',
                                    'fontWeight': 'bold', 'cursor': 'pointer'
                                }
                            ),
                            html.Div(id='gs-status', style={
                                "transform": "translateX(-50%)", "zIndex": 5, "marginTop": "8px",
                                "left": "50%", "position": "absolute"
                            }),
                            dmc.Space(h=35),  # espacio vertical de 35px
                            html.Div(id='gs-alert', className="mt-2"),
                        ], style={"position": "relative"}),
                        className="shadow p-4 rounded",
                        style={"position": "relative", "overflow": "hidden"}
                    )
                ]), width=4),

                # FTIR
                dbc.Col(html.Div([
                    dbc.Card(
                        dbc.CardBody([
                            html.H4("Upload FTIR CSV", className="text-center"),
                            dcc.Upload(
                                id='upload-ftir',
                                children=html.Div(
                                    ['Select/Drop a FTIR File'],
                                    className="text-center",
                                    style={"whiteSpace": "nowrap"}
                                ),
                                style={
                                    'width': '100%', 'height': '120px', 'lineHeight': '120px',
                                    'borderWidth': '2px', 'borderStyle': 'solid', 'borderRadius': '10px',
                                    'textAlign': 'center', 'backgroundColor': '#b0c4de', 'color': '#ffffff',
                                    'fontWeight': 'bold', 'cursor': 'pointer'
                                }
                            ),
                            html.Div(id='ftir-status', style={
                                "transform": "translateX(-50%)", "zIndex": 5, "marginTop": "8px",
                                "left": "50%", "position": "absolute"
                            }),
                            dmc.Space(h=35),  # espacio vertical de 35px
                            html.Div(id='ftir-alert', className="mt-2"),
                        ], style={"position": "relative"}),
                        className="shadow p-4 rounded",
                        style={"position": "relative", "overflow": "hidden"}
                    )
                ]), width=4)
            ])
        ], fluid=True),

        dmc.Divider(m="xl"),

        # Stores
        dcc.Store(id='upload-status', data={'tg': False, 'gs': False, 'ftir': False}),
        dcc.Store(id='show-gs-store', data=False),
        dcc.Store(id='selected-time-store', data=None),
        dcc.Store(id='fixed-ftir-list', data=[]),

        # ======= Charts =======
        html.Div(id='chart-container', style={'display': 'none'}, children=[
            dbc.Row([
                # TG% + d(TG)/dT
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            dcc.Graph(id='mass-temp-chart', style={"height": "400px", "width": "100%"}),
                            dmc.Center(dmc.Badge(id='initial-mass-badge', variant='outline',
                                                 style={'fontSize':'20px','marginTop':'10px'}))
                        ]),
                        className="shadow p-3 mb-4 rounded",
                        style={
                            "backgroundColor": "rgba(255,255,255,0.85)",
                            "height": "520px",
                            "display": "flex",
                            "flexDirection": "column",
                            "justifyContent": "center"
                        }
                    ),
                    width=6
                ),
                # Temp vs tiempo (+ GS opcional)
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            dcc.Graph(
                                id='time-temp-chart',
                                config={
                                    'editable': True,
                                    'edits': {'titleText': False, 'legendPosition': False, 'annotationPosition': False}
                                },
                                style={"height": "400px", "width": "100%"}
                            ),
                            html.Div(
                                id="gs-manual-row",
                                style={"display": "flex", "justifyContent": "center", "alignItems": "center",
                                       "gap": "16px", "marginTop": "10px"},
                                children=[
                                    dmc.Button('Add GS data', id='toggle-gs', size='xs',
                                               variant='outline', style={'fontSize':'20px'}),
                                    dcc.Input(
                                        id="manual-time-input",
                                        type="number",
                                        min=0,
                                        step=0.01,
                                        debounce=True,
                                        style={
                                            "width": "110px",
                                            "borderRadius": "16px",
                                            "border": "1.5px solid #1976d2",
                                            "padding": "6px 12px",
                                            "fontSize": "1rem",
                                            "color": "#1976d2",
                                            "background": "#f4f8fb"
                                        },
                                        placeholder="Tiempo (s)"
                                    )
                                ]
                            )
                        ]),
                        className="shadow p-3 mb-4 rounded",
                        style={
                            "backgroundColor": "rgba(255,255,255,0.85)",
                            "height": "520px",
                            "display": "flex",
                            "flexDirection": "column",
                            "justifyContent": "center"
                        }
                    ),
                    width=6
                )
            ], style={'height':'520px','alignItems':'stretch'}),

            # FTIR
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            dcc.Graph(id='ftir-graph'),
                            dmc.Center(dmc.Button(id='info-button', variant='outline', style={'width':'70%'})),
                            html.Div([
                                dmc.Group([
                                    dmc.Button(
                                        "Set spectrum",
                                        id="fix-ftir-btn",
                                        color="blue",
                                        variant="outline",
                                        style={"fontSize": "20px"}
                                    ),
                                ], style={"justifyContent": "center", "width": "100%"}),
                                dmc.Group(
                                    id="fixed-ftir-badges",
                                    style={
                                        "gap": "8px",
                                        "justifyContent": "center",
                                        "marginTop": "1rem",
                                        "flexWrap": "wrap",
                                        "display": "flex"
                                    }
                                )
                            ], style={
                                "width": "100%",
                                "display": "flex",
                                "flexDirection": "column",
                                "alignItems": "center",
                                "marginTop": "1rem"
                            }),
                        ]),
                        className="shadow p-3 mb-4 rounded",
                        style={
                            "backgroundColor": "rgba(255,255,255,0.85)",
                            "marginTop": "30px",
                            "marginBottom": "40px"
                        }
                    ),
                    width=12
                ),
                className='mt-4'
            ),
        ]),

        # ======= Chat =======
        dbc.Row([
            dbc.Col(
                html.Div(
                    id="chatbot-container",
                    style={"display": "none", "marginTop": "18px"},
                    children=[
                        dbc.Card(
                            dbc.CardBody([
                                html.H5("Chat experto TG-FTIR", className="mb-2", style={"color": "#333"}),
                                dcc.Loading(
                                    id="chat-loading",
                                    type="circle",
                                    color="#444444",
                                    fullscreen=False,
                                    children=html.Div(
                                        id="chat-history",
                                        style={
                                            "height": "260px",
                                            "overflowY": "auto",
                                            "background": "#f0f1f3",
                                            "borderRadius": "18px",
                                            "padding": "14px",
                                            "marginBottom": "10px"
                                        }
                                    )
                                ),
                                html.Div([
                                    dcc.Textarea(
                                        id="chat-input",
                                        placeholder="Escribe tu pregunta...",
                                        style={
                                            "width": "100%",
                                            "borderRadius": "18px",
                                            "padding": "12px 48px 12px 12px",
                                            "resize": "none",
                                            "minHeight": "40px",
                                            "maxHeight": "120px",
                                            "border": "1.5px solid #b0b0b0",
                                            "fontSize": "1rem",
                                            "background": "#f8f9fa"
                                        },
                                        rows=1,
                                        autoFocus=True
                                    ),
                                    html.Button(
                                        html.I(className="fa-regular fa-paper-plane"),
                                        id="send-chat",
                                        n_clicks=0,
                                        style={
                                            "position": "absolute",
                                            "right": "18px",
                                            "top": "50%",
                                            "transform": "translateY(-50%)",
                                            "border": "none",
                                            "background": "none",
                                            "color": "#444",
                                            "fontSize": "22px",
                                            "cursor": "pointer"
                                        }
                                    )
                                ], style={"position": "relative", "width": "100%"})
                            ]),
                            className="shadow p-3 mb-4 rounded",
                            style={"backgroundColor": "#fff"}
                        )
                    ]
                ),
                width=12
            ),
        ], id="chatbot-row"),
    ])
)

# ======= Upload status & parsing =======
@dash.callback(
    [
        Output('tg-status','children'),
        Output('gs-status','children'),
        Output('ftir-status','children'),
        Output('upload-status','data'),
        Output('tg-alert','children'),
        Output('gs-alert','children'),
        Output('ftir-alert','children'),
    ],
    [
        Input('upload-tg','contents'),
        Input('upload-gs','contents'),
        Input('upload-ftir','contents'),
        Input('upload-tg','filename'),
        Input('upload-gs','filename'),
        Input('upload-ftir','filename'),
    ],
    State('upload-status','data')
)
def update_status(tg_contents, gs_contents, ftir_contents,
                  tg_filename, gs_filename, ftir_filename,
                  current_status):
    global tg, gs, ftir

    ok_icon = html.I(className="fa-solid fa-circle-check", style={"color": "#000000", "fontSize": "26px"})
    ko_icon = html.I(className="fa-solid fa-arrow-up-from-bracket", style={"color": "#000000", "fontSize": "26px"})

    # Helpers para alertas
    def make_ok_alert(filename: str):
        if not filename:
            return ""
        return dmc.Alert(
            #title="File loaded",
            children=filename,
            color="green",
            variant="light",
            radius="md",
            style={"fontSize": "14px"}
        )

    def make_err_alert(msg: str):
        return dmc.Alert(
            title="Error loading file",
            children=msg,
            color="red",
            variant="light",
            radius="md",
            style={"fontSize": "14px"}
        )

    # --- TG ---
    tg_alert = ""
    if tg_contents:
        try:
            current_status['tg'] = True
            tg_status = ok_icon
            tg = pd.read_csv(decode_file(tg_contents, 'csv'), delimiter=',')
            tg_alert = make_ok_alert(tg_filename or "TG file")
        except Exception as e:
            current_status['tg'] = False
            tg_status = ko_icon
            tg_alert = make_err_alert(f"{tg_filename or 'TG'}: {e}")
    else:
        tg_status = ko_icon

    # --- GS ---
    gs_alert = ""
    if gs_contents:
        try:
            current_status['gs'] = True
            gs_status = ok_icon
            gs = pd.read_excel(decode_file(gs_contents, 'xlsx'), skiprows=4)
            gs_alert = make_ok_alert(gs_filename or "GS file")
        except Exception as e:
            current_status['gs'] = False
            gs_status = ko_icon
            gs_alert = make_err_alert(f"{gs_filename or 'GS'}: {e}")
    else:
        gs_status = ko_icon

    # --- FTIR ---
    ftir_alert = ""
    if ftir_contents:
        try:
            current_status['ftir'] = True
            ftir_status = ok_icon
            ftir = pd.read_csv(decode_file(ftir_contents, 'csv'), delimiter=';')
            ftir = ftir.dropna(axis=1, how='all')
            ftir = ftir.dropna(axis=0, how='all')
            for col in ftir.columns[0:]:
                ftir[col] = ftir[col].astype(str).str.replace(',', '.').astype(float)
            ftir_alert = make_ok_alert(ftir_filename or "FTIR file")
        except Exception as e:
            current_status['ftir'] = False
            ftir_status = ko_icon
            ftir_alert = make_err_alert(f"{ftir_filename or 'FTIR'}: {e}")
    else:
        ftir_status = ko_icon

    return tg_status, gs_status, ftir_status, current_status, tg_alert, gs_alert, ftir_alert


# Mostrar/ocultar GS
@dash.callback(
    Output('show-gs-store','data'), Output('toggle-gs','children'),
    Input('toggle-gs','n_clicks'), State('show-gs-store','data')
)
def toggle_gs(n, show):
    if n:
        new = not show
        return new, 'Remove GS data' if new else 'Add GS data'
    return show, 'Add GS data'

# ======= Charts update =======
@dash.callback(
    [
        Output('chart-container','style'),
        Output('mass-temp-chart','figure'),
        Output('time-temp-chart','figure'),
        Output('ftir-graph','figure'),
        Output('initial-mass-badge','children'),
        Output('info-button','children'),
        Output('manual-time-input', 'value'),
    ],
    [
        Input('upload-status','data'),
        Input('show-gs-store','data'),
        Input('time-temp-chart','relayoutData'),
        Input('manual-time-input', 'value'),
        Input('fixed-ftir-list','data')
    ],
)
def update_charts(status, show_gs, relayout_data, manual_time, fixed_ftir_list):
    if not status or not all(status.values()):
        return {'display':'none'}, {}, {}, {}, '', '', None

    # ---------- TG ----------
    time_tg = tg.iloc[:, 0] * 60.0
    masa_loss = tg.iloc[:, 1]
    sample_temp = tg.iloc[:, 4]
    prog_temp  = tg.iloc[:, 3]

    # ---------- GS ----------
    time_gs = gs.iloc[:, 0].astype(float)
    trans_gs = gs.iloc[:, 1].astype(float)
    df_gs = pd.DataFrame({'Time (s)': time_gs, 'Signal': trans_gs})

    # ---------- FTIR robusto (SIN absorbancia) ----------
    # Transponer: tiempos pasan a filas
    df_ftir = ftir.T.copy()
    df_ftir.columns = df_ftir.iloc[0]    # primera fila -> cabecera (nº de onda)
    df_ftir = df_ftir.iloc[1:]
    df_ftir.reset_index(inplace=True)
    df_ftir.rename(columns={df_ftir.columns[0]: 'Time (s)'}, inplace=True)

    # "Time (s)" puede venir con coma decimal aunque ya leíste el CSV a float; por si acaso:
    df_ftir['Time (s)'] = (
        df_ftir['Time (s)'].astype(str).str.replace(',', '.', regex=False).astype(float)
    )

    # Detecta columnas de número de onda:
    kept_cols = []     # nombres EXACTOS (pueden ser float, int o str) que existen en df_ftir
    wavelengths = []   # sus valores numéricos como float, mismo orden que kept_cols
    for c in list(df_ftir.columns[1:]):  # todas salvo "Time (s)"
        if isinstance(c, (int, float, np.number)):
            kept_cols.append(c)
            wavelengths.append(float(c))
        else:
            s = str(c).strip().replace(',', '.')
            try:
                val = float(s)
                kept_cols.append(c)   # usamos el label original para indexar SIN KeyError
                wavelengths.append(val)
            except Exception:
                # columna no numérica -> la ignoramos
                pass

    # Si hay columnas numéricas, nos quedamos sólo con ellas (evita KeyError por casteos)
    if kept_cols:
        df_ftir = df_ftir[['Time (s)'] + kept_cols]
        wavelengths = np.asarray(wavelengths, dtype=float)
    else:
        # Fallback imposible en archivos correctos: usamos todas tal cual y X incremental
        kept_cols = list(df_ftir.columns[1:])
        wavelengths = np.arange(len(kept_cols), dtype=float)

    # ---------- TG normalizada + DTG ----------
    init_mass = float(masa_loss.max())
    fin_mass  = float(masa_loss.min())
    if (init_mass - fin_mass) != 0:
        norm_mass = 100.0 * (masa_loss - fin_mass) / (init_mass - fin_mass)
    else:
        norm_mass = np.zeros_like(masa_loss)

    _, deriv = calc_smooth_derivative(sample_temp, norm_mass)
    if (np.max(deriv) - np.min(deriv)) != 0:
        deriv_norm = 100.0 * (deriv - np.min(deriv)) / (np.max(deriv) - np.min(deriv))
    else:
        deriv_norm = np.zeros_like(deriv)

    # Crear figura
    fig1 = go.Figure()

    # TG en eje primario (izquierda)
    fig1.add_trace(go.Scatter(
        x=sample_temp, y=norm_mass,
        mode='lines', name='TG (%)',
        line=dict(color='red'),
        yaxis="y1"
    ))

    # DTG en eje secundario (derecha)
    fig1.add_trace(go.Scatter(
        x=sample_temp, y=deriv_norm,
        mode='lines', name='d(TG)/dT (normalizado)',
        line=dict(color='blue'),
        yaxis="y2"
    ))

    # Configurar layout con doble eje
    fig1.update_layout(
        showlegend=False, #legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5),
        xaxis=dict(
            title='Temperature (°C)',
            title_font_size=20,
            showgrid=True, gridcolor='#ccc',
            showline=True, linecolor='#999'
        ),
        yaxis=dict(
            title='TG',
            title_font_color='red',
            title_font_size=20,
            tickfont=dict(color='red'),
            showgrid=True, gridcolor='#ccc',
            showline=True, linecolor='red'
        ),
        yaxis2=dict(
            title='DTG',
            title_font_color='blue',
            title_font_size=20,
            tickfont=dict(color='blue'),
            overlaying='y', side='right',
            showgrid=False, showline=True, linecolor='blue'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=10, b=70),
        font_family="Segoe UI, system-ui"
    )


    # ---------- Selección de tiempo ----------
    if ctx.triggered_id == "manual-time-input" and manual_time is not None:
        selected_time = float(manual_time)
    elif ctx.triggered_id == "time-temp-chart" and relayout_data and ('shapes[0].x0' in relayout_data or 'shapes[0].x1' in relayout_data):
        selected_time = relayout_data.get('shapes[0].x0', relayout_data.get('shapes[0].x1'))
    elif manual_time is not None:
        selected_time = float(manual_time)
    else:
        selected_time = float(df_gs['Time (s)'].min())
    selected_time = float(np.clip(selected_time, df_gs['Time (s)'].min(), df_gs['Time (s)'].max()))

    # ---------- Temp/Time + GS + línea roja ----------
    traces = [go.Scatter(x=time_tg, y=prog_temp, mode='lines', name='TG Temp', line=dict(color='#006400'))]
    if show_gs:
        traces.append(go.Scatter(x=time_gs, y=trans_gs, mode='lines', name='GS Signal', line=dict(color='#00008B'), yaxis='y2'))
    fig2 = go.Figure(data=traces)
    fig2.add_shape(type='line', x0=selected_time, x1=selected_time, y0=0, y1=1,
                   xref='x', yref='paper', line=dict(color='red', width=2), editable=True)
    layout2 = dict(
        xaxis=dict(title='Time (s)', showgrid=True, gridcolor='#ccc', showline=True, linecolor='#999'),
        yaxis=dict(title='Temperature (°C)', showgrid=not show_gs, gridcolor='#ccc', showline=True, linecolor='#006400', tickfont=dict(color='#006400')),
        dragmode='drawline', newshape_line_color='red',
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5),
        margin=dict(l=60, r=20, t=10, b=70),
        font_family="Segoe UI, system-ui"
    )
    if show_gs:
        layout2['yaxis2'] = dict(overlaying='y', side='right', title='GS Signal', showgrid=False, showline=True, linecolor='#00008B', tickfont=dict(color='#00008B'), font_family="Segoe UI, system-ui")
    fig2.update_layout(**layout2, title="", title_text="")

    # ---------- FTIR: espectro más cercano ----------
    closest_idx  = (df_ftir['Time (s)'] - selected_time).abs().argmin()
    closest_time = float(df_ftir['Time (s)'].iloc[closest_idx])
    row_data     = df_ftir.iloc[closest_idx]

    # Usa los labels originales (kept_cols) y el eje numérico (wavelengths)
    spectrum = row_data.loc[kept_cols].astype(float).to_numpy()

    fig_ftir = go.Figure()
    fig_ftir.add_trace(go.Scatter(
        x=wavelengths, y=spectrum, mode='lines',
        name=f'Espectro a {closest_time:.1f}s', line=dict(color='#333')
    ))

    # Fijados (como antes)
    if fixed_ftir_list:
        for i, f in enumerate(fixed_ftir_list):
            fig_ftir.add_trace(go.Scatter(
                x=f["x"], y=f["y"], mode='lines',
                name=f'Fijado {i+1}', line=dict(color=f["color"], width=2)
            ))

    fig_ftir.update_xaxes(title="Wavenumber (cm⁻¹)", autorange='reversed', showgrid=True, gridcolor='#ccc', showline=True, linecolor='#999')
    fig_ftir.update_yaxes(title="Transmittance (%)", showgrid=True, gridcolor='#ccc', showline=True, linecolor='#999')
    fig_ftir.update_layout(plot_bgcolor='white', paper_bgcolor='white', showlegend=False, margin=dict(l=60, r=20, t=10, b=70), font_family="Segoe UI, system-ui")

    # ---------- Info / badge ----------
    badge_text = f"Initial mass: {init_mass:.2f} mg"
    temp_interp = float(np.interp(selected_time, time_tg, sample_temp))
    btn_txt = f"Selected time (GS): {selected_time:.1f}s | Closest FTIR time: {closest_time:.1f}s | Interpolated temperature (TG): {temp_interp:.1f}°C"

    return {'display':'block'}, fig1, fig2, fig_ftir, badge_text, btn_txt, round(selected_time, 2)


# ======= Refresh (clientside) =======
from dash import Output as DOutput, Input as DInput
_app = dash.get_app()
if _app is not None:
    _app.clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks > 0) {
                window.location.reload();
            }
            return null;
        }
        """,
        DOutput('refresh-btn', 'n_clicks'),
        DInput('refresh-btn', 'n_clicks')
    )

# ======= Walkthrough: inyecta contents en los Uploads =======
@dash.callback(
    Output('upload-tg', 'contents'),
    Output('upload-gs', 'contents'),
    Output('upload-ftir', 'contents'),
    Input('walkthrough-btn-ega', 'n_clicks'),
    prevent_initial_call=True
)
def ega_walkthrough(n):
    if not n:
        raise PreventUpdate

    tg_cfg = EGA_WALKTHROUGH['tg']
    gs_cfg = EGA_WALKTHROUGH['gs']
    ftir_cfg = EGA_WALKTHROUGH['ftir']

    if not (tg_cfg['path'].exists() and gs_cfg['path'].exists() and ftir_cfg['path'].exists()):
        raise PreventUpdate

    tg_contents = _file_to_contents(tg_cfg['path'], tg_cfg['mime'])
    gs_contents = _file_to_contents(gs_cfg['path'], gs_cfg['mime'])
    ftir_contents = _file_to_contents(ftir_cfg['path'], ftir_cfg['mime'])
    return tg_contents, gs_contents, ftir_contents

# ======= FTIR: fijar/eliminar espectros (como en tu versión funcional) =======
@dash.callback(
    Output('fixed-ftir-list', 'data'),
    Input('fix-ftir-btn', 'n_clicks'),
    Input({'type': 'remove-fixed-ftir', 'index': dash.ALL}, 'n_clicks'),
    State('fixed-ftir-list', 'data'),
    State('ftir-graph', 'figure'),
    State('info-button', 'children'),
    prevent_initial_call=True
)
def manage_fixed_ftir_list(add_clicks, remove_clicks, fixed_list, fig, info_text):
    triggered_id = ctx.triggered_id
    if not triggered_id:
        raise PreventUpdate

    if triggered_id == 'fix-ftir-btn':
        if fig is None or not fig.get('data'):
            raise PreventUpdate
        current_trace = fig['data'][0]
        color = PLOTLY_COLORS[len(fixed_list) % len(PLOTLY_COLORS)]
        new_fixed_item = {"x": current_trace['x'], "y": current_trace['y'], "label": info_text, "color": color}
        return fixed_list + [new_fixed_item]

    if isinstance(triggered_id, dict) and triggered_id.get('type') == 'remove-fixed-ftir':
        idx = triggered_id['index']
        if not remove_clicks or idx >= len(remove_clicks) or not remove_clicks[idx]:
            raise PreventUpdate
        return [item for i, item in enumerate(fixed_list) if i != idx]

    raise PreventUpdate

@dash.callback(
    Output('fixed-ftir-badges', 'children'),
    Input('fixed-ftir-list', 'data')
)
def show_fixed_ftir_badges(fixed_list):
    badges = []
    for i, f in enumerate(fixed_ftir_list := (fixed_list or [])):
        badges.append(
            dmc.Badge(
                f["label"],
                color=f["color"],
                variant="filled",
                rightSection=dmc.ActionIcon(
                    html.I(className="fa-regular fa-trash-can", style={"color": "white"}),
                    id={'type': 'remove-fixed-ftir', 'index': i},
                    size="xs",
                    color="red",
                    variant="light",
                    style={"marginLeft": "8px"}
                ),
                style={"marginRight": "8px", "fontSize": "1em"}
            )
        )
    return badges

@dash.callback(
    Output("chatbot-container", "style"),
    Input('upload-status', 'data')
)
def show_chatbot(upload_status):
    if upload_status and all(upload_status.values()):
        return {"display": "block", "marginTop": "18px"}
    return {"display": "none"}

# ======= Chat (igual que tenías) =======
@dash.callback(
    [Output("chat-history", "children"),
     Output("chat-input", "value")],
    [Input("send-chat", "n_clicks"), Input("chat-input", "n_submit")],
    State("chat-input", "value"),
    State("chat-history", "children"),
    State('ftir-graph', 'figure'),
    State('info-button', 'children'),
    prevent_initial_call=True
)
def chat_with_expert(n_clicks, n_submit, user_msg, history, ftir_fig, info_text):
    global last_ftir_hash

    if not user_msg:
        raise dash.exceptions.PreventUpdate

    # Extrae espectro FTIR mostrado
    ftir_x, ftir_y = [], []
    if ftir_fig and "data" in ftir_fig and len(ftir_fig["data"]) > 0:
        trace = ftir_fig["data"][0]
        ftir_x = trace.get("x", [])
        ftir_y = trace.get("y", [])

    # Extrae tiempo y temperatura del info_button
    ftir_time, ftir_temp = "", ""
    if info_text and "|" in info_text:
        parts = info_text.split("|")
        if len(parts) >= 3:
            ftir_time = parts[0].split(":")[-1].strip()
            ftir_temp = parts[2].split(":")[-1].strip()

    # Calcula hash del FTIR actual
    current_ftir_hash = hash(tuple(ftir_x)) if ftir_x else None

    # Prompt experto
    system_prompt = (
        "Eres un experto en análisis TG-FTIR y degradación térmica de materiales. "
        "El usuario te preguntará sobre el espectro FTIR mostrado, que corresponde a una muestra en un experimento de degradación térmica. "
        "Tus tareas son: "
        "1. Analizar el espectro FTIR mostrado (te paso los datos completos de X=numero de onda y Y=transmitancia). "
        "2. Identificar todos los picos relevantes y asignar grupos funcionales o compuestos desprendidos, según la temperatura y el tiempo del experimento. "
        "3. Si el usuario lo pide, sugiere posibles mecanismos de degradación o interpreta los resultados. "
        "4. Responde de forma clara, profesional y didáctica, como un experto en TG-FTIR. "
        "Datos del espectro FTIR actual:\n"
        f"- Tiempo: {ftir_time} s\n"
        f"- Temperatura: {ftir_temp} °C\n"
        f"- Número de onda (X): {list(ftir_x)}\n"
        f"- Transmitancia (Y): {list(ftir_y)}\n"
        "Si necesitas más datos, pídelos al usuario. Si el usuario pregunta por picos, asigna los más probables según la temperatura y el contexto."
    )
    system_prompt += ("\nPor favor, estructura tu respuesta usando títulos y secciones en Markdown para mayor claridad.")

    messages = [{"role": "system", "content": system_prompt}]

    if current_ftir_hash != last_ftir_hash:
        messages.append({
            "role": "system",
            "content": (
                f"Atención: El usuario ha cargado un nuevo archivo FTIR. "
                f"Los datos actuales son:\n"
                f"- Tiempo: {ftir_time} s\n"
                f"- Temperatura: {ftir_temp} °C\n"
                f"- Número de onda (X): {list(ftir_x)}\n"
                f"- Transmitancia (Y): {list(ftir_y)}\n"
            )
        })
        last_ftir_hash = current_ftir_hash

    if history:
        for h in history:
            if isinstance(h, dict) and "props" in h and "children" in h["props"]:
                children = h["props"]["children"]
                if isinstance(children, str) and children.startswith("Tú:"):
                    messages.append({"role": "user", "content": children[3:].strip()})
                elif isinstance(children, list):
                    for child in children:
                        if hasattr(child, "props") and hasattr(child.props, "children"):
                            content = child.props.children
                            if isinstance(content, str) and content.startswith("Tú:"):
                                messages.append({"role": "user", "content": content[3:].strip()})
                            elif isinstance(content, str):
                                messages.append({"role": "assistant", "content": content})

    messages.append({"role": "user", "content": user_msg})

    try:
        if not openai.api_key:
            raise RuntimeError("OPENAI_API_KEY no está configurada.")
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=700,
            temperature=0.2,
        )
        answer = response.choices[0].message.content
    except Exception as e:
        answer = f"[Error de OpenAI: {e}]"

    new_history = (history or []) + [
        html.Div([
            html.I(className="fa-regular fa-user", style={"color": "#1976d2", "marginRight": "6px"}),
            html.Span(f"Tú: {user_msg}")
        ], style={
            "background": "#e3e6ea", "borderRadius": "14px", "padding": "8px 14px",
            "marginBottom": "4px", "display": "flex", "alignItems": "center"
        }),
        html.Div([
            html.I(className="fa-solid fa-robot", style={"color": "#444", "marginRight": "6px"}),
            dcc.Markdown(answer, style={"margin": 0})
        ], style={
            "background": "#f0f1f3", "borderRadius": "14px", "padding": "10px 16px",
            "marginBottom": "8px", "display": "flex", "alignItems": "flex-start"
        })
    ]
    return new_history, ""










