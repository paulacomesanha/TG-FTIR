import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import pandas as pd
import base64
import io
import plotly.graph_objs as go
import numpy as np
from scipy.signal import savgol_filter
import ast

dash.register_page(__name__, path='/tg-comparison', name='TG Comparison', order=2)
dash._dash_renderer._set_react_version('18.2.0')

def decode_csv_file_content(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        return io.StringIO(decoded.decode('utf-8'))
    except UnicodeDecodeError:
        return io.StringIO(decoded.decode('ISO-8859-1'))

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

def sync_vis_dict(data_json, vis_dict):
    # Si no hay archivos, devuelve dict vacío
    if not data_json:
        return {}
    # Si no hay vis_dict, todos visibles
    if not vis_dict:
        return {k: True for k in data_json.keys()}
    # Si hay nuevos archivos, añádelos como visibles
    synced = {k: vis_dict.get(k, True) for k in data_json.keys()}
    return synced
    

COLOR_PALETTE = [
    "#a3c9e2", "#f7b7a3", "#b5ead7", "#f9e79f", "#d7bde2",
    "#f5cba7", "#aed6f1", "#fad7a0", "#d2b4de", "#f7cac9"
]

layout = html.Div([
    html.Div([
        html.Div([
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
                    "transform": "translateY(-50%)"
                }
            ),
            html.H2(
                "TG Comparison",
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
        dcc.Store(id='multi-tg-data-store', data={}), 
        dcc.Store(id='show-graph-cards', data=False),
        dcc.Store(id='tg-legend-visibility', data={}),

        dbc.Card(dbc.CardBody([
            html.Div([
                dcc.Upload(
                    id='upload-multi-tg',
                    children=html.Div([
                        html.I(className="fa fa-upload", style={"marginRight": "8px", "fontSize": "22px", "color": "#1976d2"}),
                        html.Span('Arrastra o selecciona archivos TG CSV', style={"fontWeight": "bold", "color": "#1976d2"})
                    ], className="text-center"),
                    style={
                        'width': '100%',
                        'height': '70px',
                        'lineHeight': '70px',
                        'borderWidth': '2px',
                        'borderStyle': 'dashed',
                        'borderColor': '#1976d2',
                        'borderRadius': '12px',
                        'textAlign': 'center',
                        'background': '#f4f8fb',
                        'cursor': 'pointer',
                        'marginBottom': '0px'
                    },
                    multiple=True
                ),
            ], style={"display": "flex", "flexDirection": "column", "gap": "8px"}),
            html.Div(id='multi-tg-filenames-display', className="mt-3 text-muted"),
            html.Div(id='tg-unified-legend', style={"marginTop": "18px", "display": "flex", "flexWrap": "wrap", "gap": "12px", "justifyContent": "center"}),
        ]),
        className="mb-4 shadow-sm",
        style={
            "backgroundColor": "rgba(255,255,255,0.92)",
            "borderRadius": "18px",
            "boxShadow": "0 4px 24px rgba(25, 118, 210, 0.07)"
        }
        ),
        
        dmc.Divider(variant="solid", m="xl", color="#b0b0b0", size="md"),

        html.Div(id="graph-cards-container")
    ], fluid=True, className="mt-4")
])

# --- CALLBACKS ---

@dash.callback(
    [Output('multi-tg-data-store', 'data'),
     Output('multi-tg-filenames-display', 'children'),
     Output('show-graph-cards', 'data')],
    [Input('upload-multi-tg', 'contents')],
    [State('upload-multi-tg', 'filename'),
     State('multi-tg-data-store', 'data')]
)
def handle_multi_tg_uploads(list_of_contents, list_of_names, existing_data_json):
    current_data = existing_data_json.copy() if existing_data_json else {}
    
    if list_of_contents is not None:
        newly_added_files = []
        errors_encountered = []

        for c, n in zip(list_of_contents, list_of_names):
            if n in current_data:
                continue
            try:
                df = pd.read_csv(decode_csv_file_content(c), delimiter=',')
                if df.shape[1] > 4:
                    df_selected = df.iloc[:, [4, 1]].copy()
                    df_selected.columns = ['Temperature', 'Mass']
                    current_data[n] = df_selected.to_json(orient='split')
                    newly_added_files.append(n)
                else:
                    df_selected = df.iloc[:, [0, 1]].copy()
                    df_selected.columns = ['X_Value', 'Mass']
                    current_data[n] = df_selected.to_json(orient='split')
                    newly_added_files.append(n + " (fallback)")
            except Exception as e:
                errors_encountered.append(f"Error en {n}: {str(e)}")
        
        feedback_elements = []
        if newly_added_files:
            feedback_elements.append(html.P(f"Procesados: {', '.join(newly_added_files)}", className="text-success"))
        if errors_encountered:
            error_lis = [html.Li(err) for err in errors_encountered]
            feedback_elements.append(html.Details([html.Summary("Errores:"), html.Ul(error_lis)], className="text-danger"))

        show_cards = bool(current_data)
        if not current_data:
            feedback_elements.append(html.P("No hay archivos cargados.", className="text-muted"))
        else:
            loaded_files_list = [html.Li(f) for f in current_data.keys()]
            feedback_elements.insert(0, html.P(f"Total archivos: {len(current_data)}"))
            feedback_elements.append(html.Details([html.Summary("Archivos cargados:"), html.Ul(loaded_files_list)]))
        
        return current_data, feedback_elements, show_cards

    if not current_data:
        return {}, html.P("No hay archivos cargados aún.", className="text-muted"), False
    
    loaded_files_list = [html.Li(f) for f in current_data.keys()]
    return current_data, html.Div([html.P(f"Total archivos: {len(current_data)}"), html.Details([html.Summary("Archivos cargados:"),html.Ul(loaded_files_list)])]), bool(current_data)


@dash.callback(
    Output("graph-cards-container", "children"),
    Input('show-graph-cards', 'data')
)
def show_graph_cards(show_cards):
    if not show_cards:
        return ""
    return html.Div([
        dbc.Row([
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        dcc.Graph(
                            id='multi-tg-temp-graph',
                            style={'height': '350px', "width": "100%"},
                            config={
                                'editable': True,
                                'edits': {'titleText': False}
                            }
                        )
                    ]),
                    className="shadow p-3 mb-4 rounded",
                    style={
                        "backgroundColor": "rgba(255,255,255,0.85)",
                        "minHeight": "420px",
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
                            id='multi-tg-dtg-graph',
                            style={'height': '350px', "width": "100%"},
                            config={
                                'editable': True,
                                'edits': {'titleText': False}
                            }
                        )
                    ]),
                    className="shadow p-3 mb-4 rounded",
                    style={
                        "backgroundColor": "rgba(255,255,255,0.85)",
                        "minHeight": "420px",
                        "display": "flex",
                        "flexDirection": "column",
                        "justifyContent": "center"
                    }
                ),
                width=6
            ),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        dcc.Graph(
                            id='multi-tg-comparison-graph',
                            style={'height': '400px', "width": "100%"},
                            config={
                                'editable': True,
                                'edits': {'titleText': False}
                            }
                        )
                    ]),
                    className="shadow p-3 mb-4 rounded",
                    style={
                        "backgroundColor": "rgba(255,255,255,0.85)",
                        "minHeight": "470px",
                        "display": "flex",
                        "flexDirection": "column",
                        "justifyContent": "center"
                    }
                ),
                width=12
            )
        ])
    ])

# --- GRAFICO 1: Programas de temperatura ---
@dash.callback(
    Output('multi-tg-temp-graph', 'figure'),
    [Input('multi-tg-data-store', 'data'),
     Input('tg-legend-visibility', 'data')]
)
def plot_temp_programs(data_json, vis_dict):
    fig = go.Figure()
    vis_dict = sync_vis_dict(data_json, vis_dict)
    if not data_json or not any(vis_dict.values()):
        fig.update_layout(
            xaxis={'visible': False}, yaxis={'visible': False},
            plot_bgcolor='white', paper_bgcolor='white'
        )
        return fig
    for i, (filename, df_json_single) in enumerate(data_json.items()):
        if not vis_dict.get(filename, True):
            continue
        df = pd.read_json(io.StringIO(df_json_single), orient='split')
        temp_col = 'Temperature' if 'Temperature' in df.columns else 'X_Value'
        x_data = df[temp_col].astype(float)
        fig.add_trace(go.Scatter(
            x=np.arange(len(x_data)), y=x_data, mode='lines',
            name=filename.rsplit('.', 1)[0],
            line=dict(color=COLOR_PALETTE[i % len(COLOR_PALETTE)], width=2, dash="solid")
        ))
    fig.update_layout(
        xaxis_title="Time (s)",
        yaxis_title="Temperature (°C)",
        margin=dict(b=90),
        plot_bgcolor='white', paper_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='#e0e0e0'),
        yaxis=dict(showgrid=True, gridcolor='#e0e0e0')
    )
    fig.update_layout(showlegend=False)
    return fig

# --- GRAFICO 2: Derivada normalizada ---
@dash.callback(
    Output('multi-tg-dtg-graph', 'figure'),
    [Input('multi-tg-data-store', 'data'),
     Input('tg-legend-visibility', 'data')]
)
def plot_multi_tg_dtg(data_json, vis_dict):
    fig = go.Figure()
    vis_dict = sync_vis_dict(data_json, vis_dict)
    if not data_json or not any(vis_dict.values()):
        fig.update_layout(
            xaxis={'visible': False}, yaxis={'visible': False},
            plot_bgcolor='white', paper_bgcolor='white'
        )
        return fig
    for i, (filename, df_json_single) in enumerate(data_json.items()):
        if not vis_dict.get(filename, True):
            continue
        df = pd.read_json(io.StringIO(df_json_single), orient='split')
        temp_col = 'Temperature' if 'Temperature' in df.columns else 'X_Value'
        mass_col = 'Mass'
        x_data = df[temp_col].astype(float)
        y_data = df[mass_col].astype(float)
        init_mass = y_data.iloc[0]
        fin_mass = y_data.iloc[-1]
        norm_mass = 100 * (y_data - fin_mass) / (init_mass - fin_mass) if (init_mass - fin_mass) != 0 else np.zeros_like(y_data)
        y_smooth, deriv = calc_smooth_derivative(x_data.values, norm_mass.values)
        deriv_norm = 100 * (deriv - np.min(deriv)) / (np.max(deriv) - np.min(deriv)) if (np.max(deriv) - np.min(deriv)) != 0 else np.zeros_like(deriv)
        fig.add_trace(go.Scatter(
            x=x_data, y=deriv_norm, mode='lines',
            name=filename.rsplit('.', 1)[0],
            line=dict(color=COLOR_PALETTE[i % len(COLOR_PALETTE)], width=2, dash="solid")
        ))
    fig.update_layout(
        xaxis_title="Temperature (°C)" if temp_col == 'Temperature' else "X-Value (Temp or Time)",
        yaxis_title="Normalized DTG (%)",
        margin=dict(b=90),
        plot_bgcolor='white', paper_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='#e0e0e0'),
        yaxis=dict(showgrid=True, gridcolor='#e0e0e0'),
        yaxis_range=[0, 100]
    )
    fig.update_yaxes(range=[0, 100])
    fig.update_layout(showlegend=False)
    return fig

# --- GRAFICO 3: TG normalizada ---
@dash.callback(
    Output('multi-tg-comparison-graph', 'figure'),
    [Input('multi-tg-data-store', 'data'),
     Input('tg-legend-visibility', 'data')]
)
def plot_multi_tg_comparison(data_json, vis_dict):
    fig = go.Figure()
    vis_dict = sync_vis_dict(data_json, vis_dict)
    if not data_json or not any(vis_dict.values()):
        fig.update_layout(
            xaxis={'visible': False}, yaxis={'visible': False},
            plot_bgcolor='white', paper_bgcolor='white'
        )
        return fig
    for i, (filename, df_json_single) in enumerate(data_json.items()):
        if not vis_dict.get(filename, True):
            continue
        df = pd.read_json(io.StringIO(df_json_single), orient='split')
        temp_col = 'Temperature' if 'Temperature' in df.columns else 'X_Value'
        mass_col = 'Mass'
        x_data = df[temp_col].astype(float)
        y_data = df[mass_col].astype(float)
        init_mass = y_data.iloc[0]
        fin_mass = y_data.iloc[-1]
        norm_mass = 100 * (y_data - fin_mass) / (init_mass - fin_mass) if (init_mass - fin_mass) != 0 else np.zeros_like(y_data)
        fig.add_trace(go.Scatter(
            x=x_data, y=norm_mass, mode='lines',
            name=filename.rsplit('.', 1)[0],
            line=dict(color=COLOR_PALETTE[i % len(COLOR_PALETTE)], width=2, dash="solid")
        ))
    fig.update_layout(
        xaxis_title="Temperature (°C)" if temp_col == 'Temperature' else "X-Value (Temp or Time)",
        yaxis_title="Weight loss (%)",
        margin=dict(b=90),
        plot_bgcolor='white', paper_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='#e0e0e0'),
        yaxis=dict(showgrid=True, gridcolor='#e0e0e0'),
        yaxis_range=[100, 0]
    )
    fig.update_yaxes(range=[0, 100])
    fig.update_layout(showlegend=False)
    return fig

# --- REFRESH BUTTON ---
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
    Output('refresh-btn-tgcomp', 'n_clicks'),
    Input('refresh-btn-tgcomp', 'n_clicks')
)

@dash.callback(
    Output('tg-unified-legend', 'children'),
    [Input('multi-tg-data-store', 'data'),
     Input('tg-legend-visibility', 'data')]
)
def update_unified_legend(data_json, vis_dict):
    vis_dict = sync_vis_dict(data_json, vis_dict)
    if not data_json:
        return []
    legend = []
    for i, filename in enumerate(data_json.keys()):
        color = COLOR_PALETTE[i % len(COLOR_PALETTE)]
        visible = vis_dict.get(filename, True)
        icon = "fa fa-eye" if visible else "fa fa-eye-slash"
        legend.append(
            dmc.Badge(
                [
                    filename.rsplit('.', 1)[0],
                    dmc.ActionIcon(
                        html.I(className=icon, style={"color": "white"}),
                        id={'type': 'legend-eye', 'index': filename},
                        size="sm",
                        color="gray",
                        variant="subtle",
                        style={"marginLeft": "10px", "verticalAlign": "middle", "background": "transparent"}
                    )
                ],
                color=color,
                variant="filled" if visible else "outline",
                style={"fontSize": "1em", "padding": "8px 16px", "opacity": 1 if visible else 0.4}
            )
        )
    return legend

@dash.callback(
    Output('tg-legend-visibility', 'data'),
    [
        Input('multi-tg-data-store', 'data'),
        Input({'type': 'legend-eye', 'index': dash.ALL}, 'n_clicks')
    ],
    State('tg-legend-visibility', 'data'),
    prevent_initial_call=False
)
def update_visibility(data_json, n_clicks_list, vis_dict):
    """
    Updates the visibility dictionary based on user actions (file uploads or clicks on legend icons).
    """
    ctx = dash.callback_context

    # On initial load or if no files are present, return an empty dictionary.
    if not data_json:
        return {}

    # Initialize the visibility dictionary from state, ensuring it's a mutable copy.
    current_vis = vis_dict.copy() if vis_dict else {}

    # Determine what triggered the callback.
    triggered_prop_id = ctx.triggered[0]['prop_id'] if ctx.triggered else ""

    # Synchronize the visibility dictionary with the current list of files.
    # New files will be added with visibility set to True.
    # Existing files will retain their current visibility state.
    synced_vis = {filename: current_vis.get(filename, True) for filename in data_json.keys()}
    
    # Check if the trigger was a click on an "eye" icon.
    # This is more robust than checking for a specific string format.
    # It attempts to parse the ID part of the property string.
    is_eye_click = False
    clicked_filename = None

    if triggered_prop_id.endswith('.n_clicks'):
        id_str = triggered_prop_id.split('.n_clicks')[0]
        try:
            # ast.literal_eval safely parses the string representation of the ID dictionary.
            triggered_id = ast.literal_eval(id_str)
            if isinstance(triggered_id, dict) and triggered_id.get('type') == 'legend-eye':
                is_eye_click = True
                clicked_filename = triggered_id['index']
        except (ValueError, SyntaxError):
            # The ID was not a valid dictionary, so it wasn't the eye icon.
            pass

    # If an eye icon was clicked, toggle the visibility for that specific file.
    if is_eye_click and clicked_filename in synced_vis:
        synced_vis[clicked_filename] = not synced_vis[clicked_filename]

    return synced_vis



