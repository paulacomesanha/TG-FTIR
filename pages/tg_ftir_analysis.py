import dash
from dash import dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import pandas as pd
import dash_daq as daq
import base64
import io
from dash import dash_table
import dash_mantine_components as dmc
import numpy as np
import plotly.graph_objs as go
from scipy.signal import savgol_filter
import openai
from dotenv import load_dotenv
import os



dash.register_page(__name__, path='/tg-ftir-analysis', name='TG-FTIR Analysis', order=1)
dash._dash_renderer._set_react_version('18.2.0')

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def decode_file(contents, file_type='csv'):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    if file_type == 'xlsx':
        return io.BytesIO(decoded)
    elif file_type == 'csv':
        return io.StringIO(decoded.decode('ISO-8859-1'))
    else:
        raise ValueError("Unsupported file type")
    
def calc_smooth_derivative(x, y, window_length=21, polyorder=2):
    if window_length >= len(y):
        window_length = len(y) - 1 if len(y) % 2 == 0 else len(y)
    if window_length < 3:
        window_length = 3
    if window_length % 2 == 0:
        window_length += 1
    y_smooth = savgol_filter(y, window_length, polyorder)
    dy_dx = savgol_filter(y, window_length, polyorder, deriv=1, delta=np.mean(np.diff(x)))
    return y_smooth, dy_dx

# Global data holders
tg = gs = ftir = None
last_ftir_hash = None

PASTEL_COLORS = [
    "#a3c9e2", "#f7b7a3", "#b5ead7", "#f9e79f", "#d7bde2",
    "#f5cba7", "#aed6f1", "#fad7a0", "#d2b4de", "#f7cac9"
]

layout = dmc.MantineProvider(
    theme={"colorScheme": "light"},
    children=html.Div([
        html.Div([
            html.Div([
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
                html.H2(
                    "TG-FTIR Data Manager",
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

        dbc.Container([
            dbc.Row([
                dbc.Col(html.Div([
                    dbc.Card(
                        dbc.CardBody([
                            html.H4("Upload TG CSV", className="text-center"),
                            dcc.Upload(
                                id='upload-tg',
                                children=html.Div(['Select or drop a TG File'], className="text-center"),
                                style={
                                    'width': '100%', 'height': '120px', 'lineHeight': '120px',
                                    'borderWidth': '2px', 'borderStyle': 'solid', 'borderRadius': '10px',
                                    'textAlign': 'center', 'backgroundColor': '#b0c4de', 'color': '#ffffff',
                                    'fontWeight': 'bold', 'cursor': 'pointer'
                                }
                            ),
                            html.Div(id='tg-status', style={
                                "position": "absolute", "bottom": "-25px", "left": "50%",
                                "transform": "translateX(-50%)"
                            }),
                        ], style={"position": "relative"}),
                        className="shadow p-4 rounded",
                        style={"position": "relative"}
                    )
                ]), width=4),
                dbc.Col(html.Div([
                    dbc.Card(
                        dbc.CardBody([
                            html.H4("Upload GS XLSX", className="text-center"),
                            dcc.Upload(
                                id='upload-gs',
                                children=html.Div(['Select or drop a GS File'], className="text-center"),
                                style={
                                    'width': '100%', 'height': '120px', 'lineHeight': '120px',
                                    'borderWidth': '2px', 'borderStyle': 'solid', 'borderRadius': '10px',
                                    'textAlign': 'center', 'backgroundColor': '#b0c4de', 'color': '#ffffff',
                                    'fontWeight': 'bold', 'cursor': 'pointer'
                                }
                            ),
                            html.Div(id='gs-status', style={
                                "position": "absolute", "bottom": "-25px", "left": "50%",
                                "transform": "translateX(-50%)"
                            }),
                        ], style={"position": "relative"}),
                        className="shadow p-4 rounded",
                        style={"position": "relative"}
                    )
                ]), width=4),
                dbc.Col(html.Div([
                    dbc.Card(
                        dbc.CardBody([
                            html.H4("Upload FTIR CSV", className="text-center"),
                            dcc.Upload(
                                id='upload-ftir',
                                children=html.Div(['Select or drop a FTIR File'], className="text-center"),
                                style={
                                    'width': '100%', 'height': '120px', 'lineHeight': '120px',
                                    'borderWidth': '2px', 'borderStyle': 'solid', 'borderRadius': '10px',
                                    'textAlign': 'center', 'backgroundColor': '#b0c4de', 'color': '#ffffff',
                                    'fontWeight': 'bold', 'cursor': 'pointer'
                                }
                            ),
                            html.Div(id='ftir-status', style={
                                "position": "absolute", "bottom": "-25px", "left": "50%",
                                "transform": "translateX(-50%)"
                            }),
                        ], style={"position": "relative"}),
                        className="shadow p-4 rounded",
                        style={"position": "relative"}
                    )
                ]), width=4)
            ])
        ], fluid=True),

        dmc.Divider(m="xl"),

        dcc.Store(id='upload-status', data={'tg': False, 'gs': False, 'ftir': False}),
        dcc.Store(id='show-gs-store', data=False),
        dcc.Store(id='selected-time-store', data=None),
        dcc.Store(id='fixed-ftir-list', data=[]),

        html.Div(id='chart-container', style={'display': 'none'}, children=[
            dbc.Row([
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            dcc.Graph(id='mass-temp-chart', style={"height": "400px", "width": "100%"}),
                            dmc.Center(dmc.Badge(id='initial-mass-badge', variant='outline', style={'fontSize':'20px','marginTop':'10px'}))
                        ]),
                        className="shadow p-3 mb-4 rounded",
                        style={
                            "backgroundColor": "rgba(255,255,255,0.85)",
                            "height": "520px",  # <-- Fuerza altura igual
                            "display": "flex",
                            "flexDirection": "column",
                            "justifyContent": "center"
                        }
                    ),
                    width=6
                ),
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
                                style={"display": "flex", "justifyContent": "center", "alignItems": "center", "gap": "16px", "marginTop": "10px"},
                                children=[
                                    dmc.Button('Add GS data', id='toggle-gs', size='xs', variant='outline', style={'fontSize':'20px'}),
                                    dcc.Input(
                                        id="manual-time-input",
                                        type="number",
                                        min=0,
                                        step=0.01,
                                        debounce=True,  # <-- Solo actualiza al pulsar Enter o salir del campo
                                        style={
                                            "width": "110px",
                                            "borderRadius": "16px",  # Bordes circulares
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
                            "height": "520px",  # <-- Fuerza altura igual
                            "display": "flex",
                            "flexDirection": "column",
                            "justifyContent": "center"
                        }
                    ),
                    width=6
                )
            ], style={'height':'520px','alignItems':'stretch'}),
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
    type="circle",  # Spinner circular tipo "luna"
    color="#444444",  # Azul, puedes cambiar el color si quieres
    fullscreen=False,  # Solo cubre el área del chat
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
                                    "color": "#444",  # Gris oscuro
                                    "fontSize": "22px",
                                    "cursor": "pointer"
                                }
                            )
                        ], style={"position": "relative", "width": "100%"})
                    ]),
                    className="shadow p-3 mb-4 rounded",
                    style={"backgroundColor": "#fff"}  # Card blanca
                )
            ]
        ),
        width=12
    ),
], id="chatbot-row"),
    ])
)



@dash.callback(
    [Output('tg-status','children'), Output('gs-status','children'), Output('ftir-status','children'), Output('upload-status','data')],
    [Input('upload-tg','contents'), Input('upload-gs','contents'), Input('upload-ftir','contents')],
    State('upload-status','data')
)
def update_status(tg_contents, gs_contents, ftir_contents, current_status):
    global tg, gs, ftir
    if tg_contents:
        current_status['tg'] = True
        tg_status = html.Span("✔", style={"color": "green", "fontSize": "30px"})
        tg = pd.read_csv(decode_file(tg_contents, 'csv'), delimiter=',')
    else:
        tg_status = html.Span("⭕", style={"color": "red", "fontSize": "30px"})

    if gs_contents:
        current_status['gs'] = True
        gs_status = html.Span("✔", style={"color": "green", "fontSize": "30px"})
        gs = pd.read_excel(decode_file(gs_contents, 'xlsx'), skiprows=4)
    else:
        gs_status = html.Span("⭕", style={"color": "red", "fontSize": "30px"})

    if ftir_contents:
        current_status['ftir'] = True
        ftir_status = html.Span("✔", style={"color": "green", "fontSize": "30px"})
        ftir = pd.read_csv(decode_file(ftir_contents, 'csv'), delimiter=';')
        ftir = ftir.dropna(axis=1, how='all')
        ftir = ftir.dropna(axis=0, how='all')

        for col in ftir.columns[0:]:
            ftir[col] = ftir[col].astype(str).str.replace(',', '.').astype(float)
    else:
        ftir_status = html.Span("⭕", style={"color": "red", "fontSize": "30px"})

    return tg_status, gs_status, ftir_status, current_status

@dash.callback(
    Output('show-gs-store','data'), Output('toggle-gs','children'),
    Input('toggle-gs','n_clicks'), State('show-gs-store','data')
)
def toggle_gs(n, show):
    if n:
        new = not show
        return new, 'Remove GS data' if new else 'Add GS data'
    return show, 'Add GS data'

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
    #State('manual-time-input', 'value')
)
def update_charts(status, show_gs, relayout_data, manual_time, fixed_ftir_list):
    if not all(status.values()):
        return {'display':'none'}, {}, {}, {}, '', '', None

    # TG data
    time_tg = tg.iloc[:,0]*60
    masa_loss = tg.iloc[:,1]
    sample_temp = tg.iloc[:,4]
    prog_temp = tg.iloc[:,3]

    # GS data
    time_gs = gs.iloc[:,0]
    trans_gs = gs.iloc[:,1]
    df_gs = pd.DataFrame({'Time (s)': time_gs, 'Signal': trans_gs})

    df_ftir = ftir.T
    df_ftir.columns = df_ftir.iloc[0]
    df_ftir = df_ftir.iloc[1:]
    df_ftir.reset_index(inplace=True)
    df_ftir.rename(columns={df_ftir.columns[0]: 'Time (s)'}, inplace=True)

    df_ftir['Time (s)'] = (
            df_ftir['Time (s)']
            .astype(str)
            .str.replace(',', '.')       
            .astype(float)
        )

    wavelengths = [int(col) for col in df_ftir.columns[1:]]

    # Mass-%
    init_mass = masa_loss.max()
    fin_mass = masa_loss.min()
    norm_mass = 100*(masa_loss-fin_mass)/(init_mass-fin_mass)

    # Gráfico de pérdida de masa contra temperatura y su derivada
    y_smooth, deriv = calc_smooth_derivative(sample_temp, norm_mass)
    deriv_norm = 100 * (deriv - np.min(deriv)) / (np.max(deriv) - np.min(deriv))
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=sample_temp, y=norm_mass, mode='lines', name='TG (%)', line=dict(color='#800000')
    ))
    fig1.add_trace(go.Scatter(
        x=sample_temp, y=deriv_norm, mode='lines', name='d(TG)/dT (normalizado)', line=dict(color='#1f77b4')
    ))
    fig1.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.35,  # Más abajo para que no se superponga
            xanchor="center",
            x=0.5
        ),
        yaxis=dict(
            title='Weight loss (%)',
            showgrid=True, gridcolor='#ccc', showline=True, linecolor='#999'
        ),
        xaxis=dict(
            title='Temperature (°C)',
            showgrid=True, gridcolor='#ccc', showline=True, linecolor='#999'
        ),
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)'
    )

    # --- Selección de tiempo sincronizada ---
    ctx_triggered = ctx.triggered_id
    if ctx_triggered == "manual-time-input" and manual_time is not None:
        selected_time = float(manual_time)
    elif ctx_triggered == "time-temp-chart" and relayout_data and ('shapes[0].x0' in relayout_data or 'shapes[0].x1' in relayout_data):
        if 'shapes[0].x0' in relayout_data:
            selected_time = relayout_data['shapes[0].x0']
        else:
            selected_time = relayout_data['shapes[0].x1']
    elif manual_time is not None:
        selected_time = float(manual_time)
    else:
        selected_time = df_gs['Time (s)'].min()
    selected_time = np.clip(selected_time, df_gs['Time (s)'].min(), df_gs['Time (s)'].max())

    # Gráfico de temperatura (TG) con opción de GS y línea draggable
    traces = [go.Scatter(x=time_tg, y=prog_temp, mode='lines', name='TG Temp', line=dict(color='#006400'))]
    if show_gs:
        traces.append(go.Scatter(x=time_gs, y=trans_gs, mode='lines', name='GS Signal', line=dict(color='#00008B'), yaxis='y2'))
    fig2 = go.Figure(data=traces)

    # Línea vertical draggable
    fig2.add_shape(
        type='line', x0=selected_time, x1=selected_time, y0=0, y1=1,
        xref='x', yref='paper',
        line=dict(color='red', width=2), editable=True
    )

    layout2 = dict(
        xaxis=dict(
            title='Time (s)',
            showgrid=True,
            gridcolor='#ccc',
            showline=True,
            linecolor='#999'
        ),
        yaxis=dict(
            title='Temperature (°C)',
            showgrid=not show_gs,
            gridcolor='#ccc',
            showline=True,
            linecolor='#006400',
            tickfont=dict(color='#006400')
        ),
        dragmode='drawline',
        newshape_line_color='red',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    if show_gs:
        layout2['yaxis2'] = dict(
            overlaying='y',
            side='right',
            title='GS Signal',
            showgrid=False,
            showline=True,
            linecolor='#00008B',
            tickfont=dict(color='#00008B')
        )
    fig2.update_layout(**layout2)
    fig2.update_layout(
        title="",          # Elimina cualquier título
        title_text="",    # Elimina cualquier texto de título
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.35,  # Más abajo para que no se superponga
            xanchor="center",
            x=0.5
        ),
    )

    closest_idx = (df_ftir['Time (s)'] - selected_time).abs().argmin()
    closest_time = df_ftir['Time (s)'].iloc[closest_idx]

    # Obtenemos fila y espectro
    row_data = df_ftir.iloc[closest_idx]
    spectrum = row_data.iloc[1:].values.astype(float)
    fig_ftir = go.Figure()
    fig_ftir.add_trace(go.Scatter(
        x=wavelengths, y=spectrum, mode='lines',
        name=f'Espectro a {closest_time:.1f}s', line=dict(color='#333')
    ))
    # Añadir espectros fijados
    if fixed_ftir_list:
        for i, f in enumerate(fixed_ftir_list):
            fig_ftir.add_trace(go.Scatter(
                x=f["x"], y=f["y"], mode='lines',
                name=f'Fijado {i+1}',
                line=dict(color=f["color"], width=2)
            ))

    fig_ftir.update_xaxes(
            title="Wavenumber (cm⁻¹)",
            autorange='reversed', showgrid=True,
            gridcolor='#ccc', showline=True, linecolor='#999'
        )
    fig_ftir.update_yaxes(
            title="Transmitance (%)",
            showgrid=True, gridcolor='#ccc', showline=True, linecolor='#999'
        )
    fig_ftir.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            showlegend=False, margin=dict(t=20, b=60)
        )

    # Badge de masa inicial
    badge_text = f"Initial mass: {init_mass:.2f} mg"
    temp_interp = np.interp(selected_time, time_tg, sample_temp)
    btn_txt = (
        f"Selected time (GS): {selected_time:.1f}s | "
        f"Closest FTIR time: {closest_time:.1f}s | "
        f"Interpolated temperature (TG): {temp_interp:.1f}°C"
    )

    # El valor del input manual siempre sigue el valor de la barra roja
    return {'display':'block'}, fig1, fig2, fig_ftir, badge_text, btn_txt, round(float(selected_time), 2)

from dash import Output, Input, no_update

app = dash.get_app()

app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0) {
            window.location.reload();
        }
        return null;
    }
    """,
    Output('refresh-btn', 'n_clicks'),
    Input('refresh-btn', 'n_clicks')
)


@dash.callback(
    Output('fixed-ftir-list', 'data'),
    # Inputs para añadir y para eliminar
    Input('fix-ftir-btn', 'n_clicks'),
    Input({'type': 'remove-fixed-ftir', 'index': dash.ALL}, 'n_clicks'),
    # States necesarios para la lógica
    State('fixed-ftir-list', 'data'),
    State('ftir-graph', 'figure'),
    State('info-button', 'children'),
    prevent_initial_call=True
)
def manage_fixed_ftir_list(add_clicks, remove_clicks, fixed_list, fig, info_text):
    triggered_id = ctx.triggered_id
    if not triggered_id:
        raise PreventUpdate

    # --- Lógica para AÑADIR un espectro ---
    if triggered_id == 'fix-ftir-btn':
        if fig is None or not fig.get('data'):
            raise PreventUpdate
        
        # Extraemos los datos del espectro actual (siempre es el primer trazo)
        current_trace = fig['data'][0]
        color = PASTEL_COLORS[len(fixed_list) % len(PASTEL_COLORS)]
        
        new_fixed_item = {
            "x": current_trace['x'],
            "y": current_trace['y'],
            "label": info_text,
            "color": color
        }
        # Añadimos el nuevo espectro a la lista existente
        return fixed_list + [new_fixed_item]

    # --- Lógica para ELIMINAR un espectro ---
    # Comprobamos si el trigger es un botón de eliminación
    if isinstance(triggered_id, dict) and triggered_id.get('type') == 'remove-fixed-ftir':
        # El botón que se ha pulsado no debe tener 0 clics (caso inicial)
        button_that_was_clicked_index = triggered_id['index']
        if remove_clicks[button_that_was_clicked_index] is None or remove_clicks[button_that_was_clicked_index] == 0:
            raise PreventUpdate

        # Creamos una nueva lista excluyendo el elemento en el índice del botón pulsado
        new_list = [item for i, item in enumerate(fixed_list) if i != button_that_was_clicked_index]
        return new_list

    # Si el trigger no es ni añadir ni eliminar, no hacemos nada
    raise PreventUpdate

@dash.callback(
    Output('fixed-ftir-badges', 'children'),
    Input('fixed-ftir-list', 'data')
)
def show_fixed_ftir_badges(fixed_list):
    badges = []
    for i, f in enumerate(fixed_list):
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


@dash.callback(
    [Output("chat-history", "children"),
     Output("chat-input", "value")],  # <-- Añade este Output
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
        ftir_x = trace["x"]
        ftir_y = trace["y"]

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
    
    system_prompt += (
    "\nPor favor, estructura tu respuesta usando títulos y secciones en Markdown para mayor claridad."
    )

    messages = [{"role": "system", "content": system_prompt}]

    # Si el FTIR ha cambiado, añade un mensaje de sistema extra
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

    # Añade el historial como siempre
    if history:
        for h in history:
            if isinstance(h, dict) and "props" in h and "children" in h["props"]:
                children = h["props"]["children"]
                # Si es string, es un mensaje del usuario
                if isinstance(children, str) and children.startswith("Tú:"):
                    messages.append({"role": "user", "content": children[3:].strip()})
                # Si es lista, busca el texto del usuario o la respuesta del bot
                elif isinstance(children, list):
                    # Busca mensaje del usuario
                    for child in children:
                        if hasattr(child, "props") and hasattr(child.props, "children"):
                            content = child.props.children
                            if isinstance(content, str) and content.startswith("Tú:"):
                                messages.append({"role": "user", "content": content[3:].strip()})
                            elif isinstance(content, str):
                                messages.append({"role": "assistant", "content": content})

    messages.append({"role": "user", "content": user_msg})

    # Llama a OpenAI
    openai.api_key = OPENAI_API_KEY
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=700,
            temperature=0.2,
        )
        answer = response.choices[0].message.content
    except Exception as e:
        answer = f"[Error de OpenAI: {e}]"

    # Historial: usuario en burbuja azul, respuesta bot en gris y Markdown
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
    return new_history, ""  # <-- Esto limpia el textarea tras cada envío





