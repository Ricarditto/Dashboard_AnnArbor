import dash
from dash import dcc, html, Input, Output, State, no_update
import plotly.graph_objects as go
import pandas as pd

from data_handler import DataHandler

class DashboardApp:
    def __init__(self, data_filepath):
        self.data_handler = DataHandler(data_filepath)
        self.app = dash.Dash(__name__)
        self.app.title = "EV Telemetry Dashboard"
        self.app.layout = self._create_layout()
        self._register_callbacks()

    def _create_layout(self):
        lista_vehiculos = self.data_handler.get_all_vehicles()
        return html.Div(className="dashboard-container", children=[
            dcc.Store(id='trip-start-interval-store'),
            dcc.Interval(
                id='interval-component',
                interval=2000,  # <-- Intervalo de 5 segundos (5000ms)
                n_intervals=0,
                disabled=True
            ),
            html.Header(className="main-header", children=[html.H1("🛰️ EV Telemetry Dashboard")]),
            html.Div(className="control-panel", children=[
                html.Div(className="selector-container", children=[
                    html.Label("Select Vehicle:"),
                    dcc.Dropdown(
                        id='vehicle-selector',
                        options=[{'label': f'Vehicle {i}', 'value': i} for i in lista_vehiculos],
                        value=lista_vehiculos[0] if lista_vehiculos else None
                    ),
                ]),
                html.Div(className="selector-container", children=[
                    html.Label("Select Trip:"),
                    dcc.Dropdown(id='trip-selector')
                ])
            ]),
            html.Main(className="main-content", children=[
                html.Div(className="metrics-sidebar", children=[
                    html.Div(className="metric-card", children=[html.H2("Speed"), html.P(id="text-velocidad", children="-- km/h")]),
                    html.Div(className="metric-card", children=[html.H2("State of Charge (SOC)"), html.P(id="text-soc", children="-- %")]),
                    html.Div(className="metric-card", children=[html.H2("Voltage"), html.P(id="text-voltaje", children="-- V")]),
                    html.Div(className="metric-card", children=[html.H2("Instant Power"), html.P(id="text-potencia", children="-- kW")]),
                    html.Div(className="metric-card", children=[html.H2("Accumulated Energy"), html.P(id="text-energia", children="-- kWh")]),
                    html.Div(className="metric-card", children=[html.H2("Degradation Rate"), html.P(id="text-degradacion", children="--")])
                ]),
                html.Div(className="map-container", children=[dcc.Graph(id='vehicle-map', style={'height': '100%'})]),
            ])
        ])

    def _register_callbacks(self):
        @self.app.callback(
            Output('trip-selector', 'options'),
            Output('trip-selector', 'value'),
            Input('vehicle-selector', 'value')
        )
        def update_trip_selector(selected_vehicle):
            if selected_vehicle is None: return [], None
            trips = self.data_handler.get_trips_for_vehicle(selected_vehicle)
            options = [{'label': f'Trip {int(trip)}', 'value': trip} for trip in trips]
            default_value = trips[0] if trips else None
            return options, default_value
        
        @self.app.callback(
            Output('vehicle-map', 'figure'),
            Output('trip-start-interval-store', 'data'),
            Output('interval-component', 'disabled'),
            Input('trip-selector', 'value'),
            State('vehicle-selector', 'value'),
            State('interval-component', 'n_intervals'),
            prevent_initial_call=True
        )
        def initialize_trip_view(trip_id, vehicle_id, current_n_intervals):
            if not trip_id or not vehicle_id:
                return no_update, no_update, True

            trip_df = self.data_handler.get_trip_data(vehicle_id, trip_id)
            if trip_df.empty:
                return no_update, no_update, True

            fig = go.Figure()
            fig.update_layout(
                mapbox_style="open-street-map",
                mapbox_center=dict(lat=42.2808, lon=-83.7430),
                mapbox_zoom=12,
                margin={"r":0,"t":0,"l":0,"b":0},
                showlegend=False
            )
            fig.add_trace(go.Scattermapbox(lat=[], lon=[], mode='lines', line=dict(color="#16213e", width=3)))
            fig.add_trace(go.Scattermapbox(lat=[trip_df.iloc[0]['Latitude[deg]']], lon=[trip_df.iloc[0]['Longitude[deg]']], mode='markers', marker=dict(size=15, color="#e94560")))

            return fig, current_n_intervals, False

        @self.app.callback(
            Output('vehicle-map', 'figure', allow_duplicate=True),
            Output('text-velocidad', 'children'),
            Output('text-soc', 'children'),
            Output('text-voltaje', 'children'),
            Output('text-potencia', 'children'),
            Output('text-energia', 'children'),
            Input('interval-component', 'n_intervals'),
            State('vehicle-selector', 'value'),
            State('trip-selector', 'value'),
            State('trip-start-interval-store', 'data'),
            State('vehicle-map', 'figure'),
            prevent_initial_call=True
        )
        def update_playback_dashboard(n_intervals, vehicle_id, trip_id, trip_start_interval, current_figure):
            if trip_start_interval is None or not trip_id or not vehicle_id:
                return no_update

            trip_df = self.data_handler.get_trip_data(vehicle_id, trip_id)
            if trip_df.empty: return no_update

            # --- LÓGICA SIMPLIFICADA: Un punto por segundo ---
            
            # El índice actual es simplemente los segundos que han pasado desde que empezó el viaje
            elapsed_seconds = n_intervals - trip_start_interval
            
            # Usamos el módulo (%) para que la animación se reinicie automáticamente al llegar al final
            current_index = elapsed_seconds % len(trip_df)

            # Obtenemos los datos del punto actual
            current_data = trip_df.iloc[current_index]

            # Actualizamos las métricas
            velocidad = f"{current_data['Vehicle_Speed[km/h]']:.1f} km/h"
            soc = f"{current_data['HV_Battery_SOC[%]']:.1f} %"
            voltaje = f"{current_data['HV_Battery_Voltage[V]']:.1f} V"
            potencia = f"{current_data['Power[W]'] / 1000:.2f} kW" 
            energia = f"{current_data['Accum_Energy[kWh]']:.3f} kWh"

            # --- Actualización del Mapa ---
            
            # La ruta es desde el inicio hasta el punto actual
            path_so_far = trip_df.iloc[:current_index + 1]
            
            # Actualizamos la línea (traza 0)
            current_figure['data'][0]['lat'] = path_so_far['Latitude[deg]']
            current_figure['data'][0]['lon'] = path_so_far['Longitude[deg]']
            
            # Actualizamos la posición del marcador (traza 1)
            current_figure['data'][1]['lat'] = [current_data['Latitude[deg]']]
            current_figure['data'][1]['lon'] = [current_data['Longitude[deg]']]
            
            return go.Figure(current_figure), velocidad, soc, voltaje, potencia, energia
            
    def run(self, debug=True, port=8051):
        self.app.run(debug=debug, port=port)

DATA_FILEPATH = 'ev_dataset.csv' 
dashboard = DashboardApp(DATA_FILEPATH)
server = dashboard.app.server