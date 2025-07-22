import dash
from dash import html
import dash_bootstrap_components as dbc

from tg_ftir_module import build_dashboard_body, build_modals

dash.register_page(__name__, path='/', name='Home', order=0)

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
layout = dbc.Container(
    [
        # CARD 1: introductory card
        dbc.Card(
            dbc.CardBody([
                html.H1("DATA MANAGER", className="display-3 text-center mb-3",
                        style={"fontWeight": "600", "color": "#212529", "letterSpacing": "0.05em"}),
                html.P("Developed for the ease of data managing", className="text-center mb-5",
                    style={"fontSize": "1.35rem", "color": "#5a6268", "fontWeight": "300"}),
                html.Hr(style={"maxWidth": "60%", "margin": "0 auto 40px auto", "borderColor": "#ced4da"}),
                html.Div([
                    html.P("Select an option from the sidebar to begin:",
                        className="text-center mt-4 mb-3",
                        style={"fontSize": "1.15rem", "color": "#495057"}),
                    html.Ul([
                        html.Li("TG-FTIR Analysis: Visualize and interact with coupled thermogravimetric and infrared spectroscopy data.",
                                style={"padding": "10px 0", "color": "#343a40", "fontSize": "1.05rem"}),
                        html.Li("TG Comparison: Upload and compare multiple thermogravimetric analysis curves on a single chart.",
                                style={"padding": "10px 0", "color": "#343a40", "fontSize": "1.05rem"}),
                    ], style={"listStyle": "none", "paddingLeft": 0, "textAlign": "left", "maxWidth": "90%"}, className="mx-auto")
                ], className="mt-3")
            ]),
            style=CARD_STYLE
        ),
        dbc.Card(
            dbc.CardBody([
                html.H1("TG-FTIR INTERACTIVE SYSTEM", className= "display-3 text-center mb-3", style={"fontWeight": 600}),
                build_dashboard_body()
            ], style={"overflow": "visible"}),
            style={**CARD_STYLE, "marginTop": "2rem", "overflow": "visible"}
        ),
        # Modals
        *build_modals(),

    ],
    fluid=True, className="mb-4"
)