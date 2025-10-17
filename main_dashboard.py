import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import pandas as pd

from data_handler import DataHandler

class DashboardApp:
    def __init__(self, data_filepath):
        self.data_handler = DataHandler(data_filepath)
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        self.app.title = "EV Telemetry Dashboard"
        self.trip_colors = ['#BB86FC', '#03DAC6']
        self.app.layout = self._create_layout()
        self._register_callbacks()

    def _create_layout(self):
        all_vehicles = self.data_handler.get_all_vehicles()
        
        default_vehicle_id = 455
        default_trip_options = []
        if default_vehicle_id in all_vehicles:
            trips = self.data_handler.get_trips_for_vehicle(default_vehicle_id)
            default_trip_options = [{'label': f'Trip {int(trip)}', 'value': trip} for trip in trips]

        slot1 = html.Div(className="selector-slot", children=[
            html.H3(f"Vehicle 1 Selection"),
            dcc.Store(id='trip-start-interval-store-1'),
            html.Label("Select Vehicle:"),
            dcc.Dropdown(
                id='vehicle-selector-1',
                options=[{'label': f'Vehicle {v}', 'value': v} for v in all_vehicles],
                value=455,
                className="vehicle-dropdown"
            ),
            html.Label("Select Trip:"),
            dcc.Dropdown(
                id='trip-selector-1',
                options=default_trip_options,
                value=1197,
                className="trip-dropdown"
            )
        ])
        
        slot2 = html.Div(className="selector-slot", children=[
            html.H3(f"Vehicle 2 Selection"),
            dcc.Store(id='trip-start-interval-store-2'),
            html.Label("Select Vehicle:"),
            dcc.Dropdown(
                id='vehicle-selector-2',
                options=[{'label': f'Vehicle {v}', 'value': v} for v in all_vehicles],
                value=455,
                className="vehicle-dropdown"
            ),
            html.Label("Select Trip:"),
            dcc.Dropdown(
                id='trip-selector-2',
                options=default_trip_options,
                value=1648,
                className="trip-dropdown"
            )
        ])

        control_slots = [slot1, slot2]

        metric_sidebars = []
        for i in range(1, 3):
            sidebar = html.Div(className="metrics-sidebar", children=[
                html.H3(f"Vehicle {i} Live Metrics", style={'color': self.trip_colors[i-1]}),
                html.Div(className="metric-card", children=[html.H2("Speed"), html.P(id=f"text-velocidad-{i}", children="-- km/h")]),
                html.Div(className="metric-card", children=[html.H2("State of Charge (SOC)"), html.P(id=f"text-soc-{i}", children="-- %")]),
                html.Div(className="metric-card", children=[html.H2("Voltage"), html.P(id=f"text-voltaje-{i}", children="-- V")]),
                html.Div(className="metric-card", children=[html.H2("Instant Power"), html.P(id=f"text-potencia-{i}", children="-- kW")]),
                html.Div(className="metric-card", children=[html.H2("Accumulated Energy"), html.P(id=f"text-energia-{i}", children="-- kWh")]),
                html.Div(className="metric-card", children=[html.H2("MDR"), html.P(id=f"text-mdr-{i}", children="--")]),
                html.Div(className="metric-card", children=[html.H2("Degradation Rate"), html.P(id=f"text-degradation-{i}", children="--")]),
            ])
            metric_sidebars.append(sidebar)

        return html.Div(className="dashboard-container", children=[
            dcc.Interval(id='interval-component', interval=500, n_intervals=0),
            html.Header(className="main-header", children=[html.H1("🛰️ EV-Sim Dashboard")]),
            html.Div(className="control-panel-multi", children=control_slots),
            html.Main(className="main-content-dual-metrics", children=[
                *metric_sidebars,
                html.Div(className="map-container-dual-metrics", children=[
                    dcc.Graph(id='vehicle-map', style={'height': '100%'})
                ]),
            ])
        ])

    def _register_callbacks(self):
        def create_callback_functions(i):
            @self.app.callback(
                Output(f'trip-selector-{i}', 'options'),
                Input(f'vehicle-selector-{i}', 'value')
            )
            def update_trip_options(selected_vehicle):
                if selected_vehicle is None: return []
                trips = self.data_handler.get_trips_for_vehicle(selected_vehicle)
                return [{'label': f'Trip {int(trip)}', 'value': trip} for trip in trips]

            @self.app.callback(
                Output(f'trip-start-interval-store-{i}', 'data'),
                Input(f'trip-selector-{i}', 'value'),
                State('interval-component', 'n_intervals')
            )
            def reset_trip_timer(trip_id, n_intervals):
                return n_intervals

        for i in range(1, 3):
            create_callback_functions(i)

        @self.app.callback(
            # --- NUEVOS OUTPUTS AÑADIDOS AL CALLBACK ---
            Output('vehicle-map', 'figure'),
            # Vehículo 1
            Output('text-velocidad-1', 'children'),
            Output('text-soc-1', 'children'),
            Output('text-voltaje-1', 'children'),
            Output('text-potencia-1', 'children'),
            Output('text-energia-1', 'children'),
            Output('text-degradation-1', 'children'),
            Output('text-mdr-1', 'children'),
            # Vehículo 2
            Output('text-velocidad-2', 'children'),
            Output('text-soc-2', 'children'),
            Output('text-voltaje-2', 'children'),
            Output('text-potencia-2', 'children'),
            Output('text-energia-2', 'children'),
            Output('text-degradation-2', 'children'),
            Output('text-mdr-2', 'children'),
            # Inputs y States
            Input('interval-component', 'n_intervals'),
            State('vehicle-selector-1', 'value'),
            State('vehicle-selector-2', 'value'),
            State('trip-selector-1', 'value'),
            State('trip-selector-2', 'value'),
            State('trip-start-interval-store-1', 'data'),
            State('trip-start-interval-store-2', 'data'),
        )
        def update_multi_trip_dashboard(n_intervals, 
                                        vehicle_id_1, vehicle_id_2,
                                        trip_id_1, trip_id_2,
                                        start_interval_1, start_interval_2):
            
            vehicle_ids = [vehicle_id_1, vehicle_id_2]
            trip_ids = [trip_id_1, trip_id_2]
            start_intervals = [start_interval_1, start_interval_2]
            
            fig = go.Figure()
            fig.update_layout(
                mapbox_style="open-street-map",
                mapbox_center=dict(lat=42.2808, lon=-83.7430),
                mapbox_zoom=11.5,
                margin={"r":0, "t":0, "l":0, "b":0},
                showlegend=False
            )
            
            # --- LISTA DE MÉTRICAS ACTUALIZADA CON LOS NUEVOS VALORES ---
            metrics_outputs = ["-- km/h", "-- %", "-- V", "-- kW", "-- kWh", "--", "--"] * 2

            for i in range(2):
                vehicle_id = vehicle_ids[i]
                trip_id = trip_ids[i]
                start_interval = start_intervals[i]

                if vehicle_id and trip_id and start_interval is not None:
                    trip_df = self.data_handler.get_trip_data(vehicle_id, trip_id)
                    if trip_df.empty: continue

                    elapsed_seconds = n_intervals - start_interval
                    current_index = elapsed_seconds % len(trip_df)
                    current_data = trip_df.iloc[current_index]
                    path_so_far = trip_df.iloc[:current_index + 1]

                    fig.add_trace(go.Scattermapbox(
                        lat=path_so_far['Latitude[deg]'],
                        lon=path_so_far['Longitude[deg]'],
                        mode='lines',
                        line=dict(color=self.trip_colors[i], width=3)
                    ))

                    fig.add_trace(go.Scattermapbox(
                        lat=[current_data['Latitude[deg]']],
                        lon=[current_data['Longitude[deg]']],
                        mode='markers',
                        marker=dict(size=15, color=self.trip_colors[i])
                    ))

                    velocidad = f"{current_data['Vehicle_Speed[km/h]']:.1f} km/h"
                    soc = f"{current_data['HV_Battery_SOC[%]']:.1f} %"
                    voltaje = f"{current_data['HV_Battery_Voltage[V]']:.1f} V"
                    potencia = f"{current_data['Power[W]'] / 1000:.2f} kW"
                    energia = f"{current_data['Accum_Energy[kWh]']:.3f} kWh"
                    
                    # --- ÍNDICE AJUSTADO PARA INCLUIR LAS 7 MÉTRICAS POR VEHÍCULO ---
                    metrics_start_index = i * 7
                    metrics_outputs[metrics_start_index] = velocidad
                    metrics_outputs[metrics_start_index + 1] = soc
                    metrics_outputs[metrics_start_index + 2] = voltaje
                    metrics_outputs[metrics_start_index + 3] = potencia
                    metrics_outputs[metrics_start_index + 4] = energia
                    # Los valores de Degradation y MDR permanecen como "--"

            return [fig] + metrics_outputs
            
    def run(self, debug=True, port=8051):
        self.app.run(debug=debug, port=port)

DATA_FILEPATH = 'ev_dataset.csv' 
dashboard = DashboardApp(DATA_FILEPATH)
server = dashboard.app.server
if __name__ == '__main__':
    dashboard.run(debug=False)