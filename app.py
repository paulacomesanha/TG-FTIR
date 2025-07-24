import dash_mantine_components as dmc
import dash
from dash import Dash, html, dcc, Input, Output, State, ctx
import dash_bootstrap_components as dbc
from threading import Timer
import webbrowser
import socket
from home_dashboard import register_callbacks

# --- Helper functions ---
def find_free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

def open_browser(port):
    webbrowser.open_new(f"http://127.0.0.1:{port}/")

# --- App Initialization ---
external_stylesheets = [
    dbc.themes.BOOTSTRAP,
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
]
dash._dash_renderer._set_react_version('18.2.0')
app = Dash(__name__, use_pages=True, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
register_callbacks(app)
server = app.server

# --- Sidebar Configuration ---
SIDEBAR_WIDTH_OPEN = "20rem"
SIDEBAR_WIDTH_COLLAPSED = "5.5rem"

SIDEBAR_STYLE_BASE = {
    "position": "fixed",  # <-- ¡ESTO SOLUCIONA EL PROBLEMA!
    "top": 0, "left": 0, "bottom": 0,
    "transition": "width .3s ease, padding .3s ease", 
    "backgroundColor": "#e9ecef", 
    "borderRight": "1px solid #dee2e6", 
    "overflowY": "auto", 
    "height": "100vh", 
    "flexShrink": 0, 
    "boxSizing": "border-box" 
}
SIDEBAR_STYLE_OPENED = {**SIDEBAR_STYLE_BASE, "width": SIDEBAR_WIDTH_OPEN, "padding": "1.5rem 1rem"}
SIDEBAR_STYLE_COLLAPSED = {**SIDEBAR_STYLE_BASE, "width": SIDEBAR_WIDTH_COLLAPSED, "padding": "1rem 0.25rem"}

def generate_sidebar_nav_links(is_open):
    link_items = [
        {"href": "/", "icon": "fas fa-home", "text": "Home"},
        {"href": "/tg-comparison", "icon": "fas fa-thermometer-half", "text": "Thermogravimetric Analysis"},
        {"href": "/tg-ftir-analysis", "icon": "fas fa-chart-line", "text": "Evolved Gas Analysis"},    
    ]
    nav_links = []
    for item in link_items:
        if is_open: 
            nav_link = dbc.NavLink(
                [html.I(className=f"{item['icon']} me-3 fa-fw"), html.Span(item['text'])],
                href=item['href'], active="exact", className="py-2 fs-5"
            )
        else: 
            nav_link = dbc.NavLink(
                [html.I(className=f"{item['icon']} fa-lg fa-fw")], 
                href=item['href'], active="exact", className="my-3 text-center",
                style={"padding": "0.5rem 0"}
            )
        nav_links.append(nav_link)
    return dbc.Nav(nav_links, vertical=True, pills=True)

# --- App Layout ---
app.layout = dmc.MantineProvider(
    theme={"colorScheme": "light"},
    children=html.Div( 
        style={
            "display": "flex", 
            "flexDirection": "row", 
            "width": "100vw", 
            "height": "100vh", 
            "overflow": "hidden", 
            "backgroundColor": "#e9ecef"  
        },
        children=[
            dcc.Location(id="url", refresh=False), 
            dcc.Store(id='sidebar-is-open', data=True), 

            html.Div(id="sidebar", children=[ 
                html.Div([
                    html.Button(
                        html.I(id="sidebar-toggle-icon", className="fas fa-times"), 
                        id="btn_sidebar_toggle",
                        className="btn btn-light", 
                        style={
                            "fontSize": "1.2rem", "padding": "0.3rem 0.6rem",
                            "position": "absolute", "top": "10px", "right": "10px", 
                        }
                    ),
                    html.H4("MENU", className="display-6 text-center mt-2 mb-0", id="sidebar-title",
                            style={"color":"#343a40", "fontWeight": "500", "transition": "opacity .2s ease, font-size .2s ease"})
                ], style={"paddingBottom": "1rem", "minHeight": "60px", "position":"relative"}), 
                html.Hr(id="sidebar-hr", style={"borderColor": "#adb5bd", "transition": "opacity .2s ease"}),
                html.Div(id="sidebar-nav-content-div")
            ]),
            html.Div(id="page_content_div", children=dash.page_container) 
        ]
    )
)

# --- Callbacks ---
@app.callback(
    [Output("sidebar", "style"),
     Output("sidebar-toggle-icon", "className"),
     Output("sidebar-is-open", "data"),
     Output("sidebar-nav-content-div", "children"),
     Output("sidebar-title", "style"),
     Output("sidebar-hr", "style")],
    [Input("btn_sidebar_toggle", "n_clicks")],
    [State("sidebar-is-open", "data")]
)
def manage_sidebar_appearance(n_clicks, sidebar_is_open_current):
    triggered_id = ctx.triggered_id
    new_sidebar_is_open = sidebar_is_open_current 

    if triggered_id == "btn_sidebar_toggle": 
        new_sidebar_is_open = not sidebar_is_open_current 

    if new_sidebar_is_open:
        sidebar_style_actual = SIDEBAR_STYLE_OPENED
        toggle_icon_class = "fas fa-times" 
        nav_content = generate_sidebar_nav_links(True) 
        sidebar_title_style = {"color":"#343a40", "fontWeight": "500", "opacity": 1, "fontSize": "1.75rem", "transition": "opacity .3s ease .1s, font-size .3s ease"}
        sidebar_hr_style = {"borderColor": "#adb5bd", "opacity": 1, "transition": "opacity .3s ease .1s"}
    else: 
        sidebar_style_actual = SIDEBAR_STYLE_COLLAPSED
        toggle_icon_class = "fas fa-bars"   
        nav_content = generate_sidebar_nav_links(False) 
        sidebar_title_style = {"color":"#343a40", "fontWeight": "500", "opacity": 0, "fontSize": "0rem", "transition": "opacity .2s ease, font-size .2s ease"} 
        sidebar_hr_style = {"borderColor": "#adb5bd", "opacity": 0, "transition": "opacity .2s ease"} 

    return sidebar_style_actual, toggle_icon_class, new_sidebar_is_open, nav_content, sidebar_title_style, sidebar_hr_style

@app.callback(
    Output("page_content_div", "style"),
    [Input("url", "pathname"),             
     Input("sidebar-is-open", "data")]  
)
def style_page_content_wrapper(pathname, sidebar_is_open):
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
    }

    if pathname == '/': 
        home_page_wrapper_style = {
            **base_content_style,
            "background": "#f8f9fa",    
            "display": "flex", 
            "flexDirection": "column",         
            "alignItems": "center",     
            "justifyContent": "flex-start", 
            "padding": "2rem"           
        }
        return home_page_wrapper_style
    else: 
        other_pages_wrapper_style = {
            **base_content_style,
            "background": "#f8f9fa",  # O el color que prefieras
            "padding": "2rem"
        }
        return other_pages_wrapper_style

# En pages/tg_ftir_analysis.py
import dash_mantine_components as dmc
from dash import html

layout = dmc.MantineProvider(
    theme={"colorScheme": "light"},
    children=html.Div([
        # ...tu contenido...
    ], style={
        "padding": "2rem 1rem",  # Solo padding interno, NO marginLeft ni background
        "width": "100%",         # Opcional, para asegurar que ocupa todo el espacio
        "boxSizing": "border-box"
    })
)

if __name__ == '__main__':
    port = find_free_port()
    Timer(1, open_browser, args=[port]).start()
    app.run(debug=False, use_reloader=False, port=port)
