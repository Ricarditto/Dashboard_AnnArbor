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
        # Colors for the two vehicle traces
        self.trip_colors = ['#e94560', '#2a72de']
        self.app.layout = self._create_layout()
        self._register_callbacks()

    def _create_layout(self):
        all_vehicles = self.data_handler.get_all_vehicles()
        
        # Create 2 control slots for vehicle/trip selection
        control_slots = []
        for i in range(1, 3):
            slot = html.Div(className="selector-slot", children=[
                html.H3(f"Trip Slot {i}"),
                dcc.Store(id=f'trip-start-interval-store-{i}'),
                dcc.Dropdown(
                    id=f'vehicle-selector-{i}',
                    options=[{'label': f'Vehicle {v}', 'value': v} for v in all_vehicles],
                    placeholder="Select Vehicle...",
                    className="vehicle-dropdown"
                ),
                dcc.Dropdown(
                    id=f'trip-selector-{i}',
                    placeholder="Select Trip...",
                    className="trip-dropdown"
                )
            ])
            control_slots.append(slot)

        # Create 2 metric sidebars
        metric_sidebars = []
        for i in range(1, 3):
            sidebar = html.Div(className="metrics-sidebar", children=[
                html.H3(f"Vehicle {i} Metrics", style={'color': self.trip_colors[i-1], 'textAlign': 'center'}),
                html.Div(className="metric-card", children=[html.H2("Speed"), html.P(id=f"text-velocidad-{i}", children="-- km/h")]),
                html.Div(className="metric-card", children=[html.H2("State of Charge (SOC)"), html.P(id=f"text-soc-{i}", children="-- %")]),
                html.Div(className="metric-card", children=[html.H2("Voltage"), html.P(id=f"text-voltaje-{i}", children="-- V")]),
                html.Div(className="metric-card", children=[html.H2("Instant Power"), html.P(id=f"text-potencia-{i}", children="-- kW")]),
                html.Div(className="metric-card", children=[html.H2("Accumulated Energy"), html.P(id=f"text-energia-{i}", children="-- kWh")]),
            ])
            metric_sidebars.append(sidebar)

        return html.Div(className="dashboard-container", children=[
            dcc.Interval(id='interval-component', interval=1000, n_intervals=0),
            html.Header(className="main-header", children=[html.H1("🛰️ EV Dual-Trip Dashboard")]),
            html.Div(className="control-panel-multi", children=control_slots),
            html.Main(className="main-content-dual-metrics", children=[
                *metric_sidebars, # Unpack the two sidebars
                html.Div(className="map-container-dual-metrics", children=[
                    dcc.Graph(id='vehicle-map', style={'height': '100%'})
                ]),
            ])
        ])

    def _register_callbacks(self):
        # Function to generate callbacks for each slot (1 and 2)
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

        # Create the callbacks for slot 1 and slot 2
        for i in range(1, 3):
            create_callback_functions(i)

        # Main unified callback to update map and all metrics
        @self.app.callback(
            Output('vehicle-map', 'figure'),
            # Outputs for Vehicle 1
            Output('text-velocidad-1', 'children'),
            Output('text-soc-1', 'children'),
            Output('text-voltaje-1', 'children'),
            Output('text-potencia-1', 'children'),
            Output('text-energia-1', 'children'),
            # Outputs for Vehicle 2
            Output('text-velocidad-2', 'children'),
            Output('text-soc-2', 'children'),
            Output('text-voltaje-2', 'children'),
            Output('text-potencia-2', 'children'),
            Output('text-energia-2', 'children'),
            # Inputs and States
            Input('interval-component', 'n_intervals'),
            [State(f'vehicle-selector-{i}', 'value') for i in range(1, 3)],
            [State(f'trip-selector-{i}', 'value') for i in range(1, 3)],
            [State(f'trip-start-interval-store-{i}', 'data') for i in range(1, 3)]
        )
        def update_multi_trip_dashboard(n_intervals, vehicle_ids, trip_ids, start_intervals):
            fig = go.Figure()
            fig.update_layout(
                mapbox_style="open-street-map",
                mapbox_center=dict(lat=42.2808, lon=-83.7430),
                mapbox_zoom=12,
                margin={"r":0, "t":0, "l":0, "b":0},
                showlegend=False
            )
            
            # Initialize metrics for both vehicles with default values
            metrics_outputs = ["-- km/h", "-- %", "-- V", "-- kW", "-- kWh"] * 2

            for i in range(2): # Iterate for vehicle 1 and vehicle 2
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

                    # Add trip route (line) to map
                    fig.add_trace(go.Scattermapbox(
                        lat=path_so_far['Latitude[deg]'],
                        lon=path_so_far['Longitude[deg]'],
                        mode='lines',
                        line=dict(color=self.trip_colors[i], width=3)
                    ))

                    # Add vehicle marker to map
                    fig.add_trace(go.Scattermapbox(
                        lat=[current_data['Latitude[deg]']],
                        lon=[current_data['Longitude[deg]']],
                        mode='markers',
                        marker=dict(size=15, color=self.trip_colors[i])
                    ))

                    # Calculate and update the metrics for the current vehicle (i)
                    velocidad = f"{current_data['Vehicle_Speed[km/h]']:.1f} km/h"
                    soc = f"{current_data['HV_Battery_SOC[%]']:.1f} %"
                    voltaje = f"{current_data['HV_Battery_Voltage[V]']:.1f} V"
                    potencia = f"{current_data['Power[W]'] / 1000:.2f} kW"
                    energia = f"{current_data['Accum_Energy[kWh]']:.3f} kWh"
                    
                    # Place the calculated metrics in the correct position in the output list
                    metrics_start_index = i * 5
                    metrics_outputs[metrics_start_index] = velocidad
                    metrics_outputs[metrics_start_index + 1] = soc
                    metrics_outputs[metrics_start_index + 2] = voltaje
                    metrics_outputs[metrics_start_index + 3] = potencia
                    metrics_outputs[metrics_start_index + 4] = energia

            # The final return statement includes the figure and all 10 metric values
            return [fig] + metrics_outputs
            
    def run(self, debug=True, port=8051):
        self.app.run(debug=debug, port=port)

DATA_FILEPATH = 'ev_dataset.csv'
dashboard = DashboardApp(DATA_FILEPATH)
server = dashboard.app.server
dashboard.run(debug=False)