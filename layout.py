from dash import dcc, html

def create_layout():
    return html.Div(className="dashboard-container", children=[
        
        # --- Cabecera ---
        html.Header(className="main-header", children=[
            html.H1("🛰️ Dashboard de Telemetría Vehicular EV")
        ]),

        # --- Cuerpo Principal (Mapa y Métricas) ---
        html.Main(className="main-content", children=[
            
            # --- Columna de Métricas ---
            html.Div(className="metrics-sidebar", children=[
                html.Div(className="metric-card", children=[
                    html.H2("Velocidad"),
                    html.P(id="text-velocidad", children="-- km/h")
                ]),
                html.Div(className="metric-card", children=[
                    html.H2("Estado de Carga (SOC)"),
                    html.P(id="text-soc", children="-- %")
                ]),
                html.Div(className="metric-card", children=[
                    html.H2("Voltaje"),
                    html.P(id="text-voltaje", children="-- V")
                ]),
                html.Div(className="metric-card", children=[
                    html.H2("Potencia Instantánea"),
                    html.P(id="text-potencia", children="-- kW")
                ]),
                html.Div(className="metric-card", children=[
                    html.H2("Energía Acumulada"),
                    html.P(id="text-energia", children="-- kWh")
                ]),
                html.Div(className="metric-card", children=[
                    html.H2("Tasa de Degradación"),
                    html.P(id="text-degradacion", children="--")
                ]),
            ]),

            # --- Columna del Mapa ---
            html.Div(className="map-container", children=[
                dcc.Graph(id='vehicle-map', style={'height': '100%'})
            ]),
        ])
    ])