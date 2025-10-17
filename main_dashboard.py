import dash
from dash import dcc, html, Input, Output, State, Patch
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from data_handler import DataHandler

class DashboardApp:
    def __init__(self, data_filepath):
        self.data_handler = DataHandler(data_filepath)
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        self.app.title = "EV Degradation Simulator"
        self.trip_color = '#BB86FC'
        
        # Data from the PDF for MDR calculation
        self.dist_points = np.array([0, 60, 65, 70, 75, 80, 85, 90, 95, 100, 110])
        self.prob_points = np.array([0, 0, 0.05, 0.15, 0.3, 0.4, 0.55, 0.7, 0.88, 1.0, 1.0])

        self.app.layout = self._create_layout()
        self._register_callbacks()

    def _create_layout(self):
        all_vehicles = self.data_handler.get_all_vehicles()
        default_vehicle_id = 455
        default_trip_id = 2323
        default_trip_options = [{'label': f'Trip {default_trip_id}', 'value': default_trip_id}]

        stores = [
            dcc.Store(id='simulation-state-store', data={
                'cycle_count': 0, 'total_distance_offset': 0.0, 'start_interval': 0
            })
        ]

        control_panel = html.Div(className="selector-slot", children=[
            html.H3("Simulation Control"),
            html.Label("Vehicle:"),
            dcc.Dropdown(id='vehicle-selector', options=[{'label': f'Vehicle {v}', 'value': v} for v in all_vehicles], value=default_vehicle_id),
            html.Label("Trip:"),
            dcc.Dropdown(id='trip-selector', options=default_trip_options, value=default_trip_id)
        ])

        metrics_sidebar = html.Div(className="metrics-sidebar", children=[
            html.H3("Live Trip Metrics", style={'color': self.trip_color}),
            html.Div(className="metric-card", children=[html.H2("Speed"), html.P(id="text-velocidad", children="-- km/h")]),
            html.Div(className="metric-card", children=[html.H2("State of Charge (SOC)"), html.P(id="text-soc", children="-- %")]),
            html.H3("Cumulative Simulation", style={'color': '#03DAC6', 'marginTop': '20px'}),
            html.Div(className="metric-card", children=[html.H2("Cycle Count"), html.P(id="text-cycle-count", children="0")]),
            html.Div(className="metric-card", children=[html.H2("Total Distance"), html.P(id="text-total-distance", children="0.0 km")]),
            html.Div(id="mdr-card", className="mdr-card-base", children=[html.H2("MDR (Probability)"), html.P(id="text-mdr", children="0.0 %")]),
        ])

        return html.Div(className="dashboard-container", children=[
            *stores,
            dcc.Interval(id='interval-component', interval=100, n_intervals=0),
            html.Header(className="main-header", children=[html.H1("🛰️ Repetitive Trip Simulator")]),
            html.Div(className="control-panel-multi", style={'gridTemplateColumns': '1fr'}, children=[control_panel]),
            html.Main(className="main-content-dual-metrics", children=[
                metrics_sidebar,
                # El mapa ahora se inicializa con una figura vacía
                html.Div(className="map-container-dual-metrics", children=[dcc.Graph(id='vehicle-map', style={'height': '100%'}, figure={})]),
            ])
        ])

    def _register_callbacks(self):
        # Callback para actualizar las opciones de viaje (sin cambios)
        @self.app.callback(
            Output('trip-selector', 'options'),
            Output('trip-selector', 'value'),
            Input('vehicle-selector', 'value'),
            prevent_initial_call=True
        )
        def update_trip_options(selected_vehicle):
            if selected_vehicle is None: return [], None
            trips = self.data_handler.get_trips_for_vehicle(selected_vehicle)
            options = [{'label': f'Trip {int(trip)}', 'value': trip} for trip in trips]
            return options, trips[0] if trips else None

        # --- NUEVO CALLBACK: Inicializa el mapa solo cuando cambia el viaje ---
        @self.app.callback(
            Output('vehicle-map', 'figure'),
            Output('simulation-state-store', 'data'),
            Input('trip-selector', 'value'),
            State('interval-component', 'n_intervals')
        )
        def initialize_map_and_simulation(trip_id, n_intervals):
            fig = go.Figure()
            fig.update_layout(
                mapbox_style="open-street-map",
                mapbox_center=dict(lat=42.2850, lon=-83.7380),
                mapbox_zoom=12.5,
                margin={"r":0, "t":0, "l":0, "b":0},
                showlegend=False
            )
            # Añade trazas vacías que se actualizarán después
            fig.add_trace(go.Scattermapbox(lat=[], lon=[], mode='lines', line=dict(color=self.trip_color, width=3)))
            fig.add_trace(go.Scattermapbox(lat=[], lon=[], mode='markers', marker=dict(size=15, color=self.trip_color)))

            # Resetea el estado de la simulación
            new_sim_state = {'cycle_count': 0, 'total_distance_offset': 0.0, 'start_interval': n_intervals}
            
            return fig, new_sim_state

        # --- CALLBACK PRINCIPAL MODIFICADO: Ahora solo actualiza datos y usa Patch ---
        @self.app.callback(
            Output('vehicle-map', 'figure', allow_duplicate=True),
            Output('text-velocidad', 'children'),
            Output('text-soc', 'children'),
            Output('text-cycle-count', 'children'),
            Output('text-total-distance', 'children'),
            Output('text-mdr', 'children'),
            Output('simulation-state-store', 'data', allow_duplicate=True),
            Input('interval-component', 'n_intervals'),
            State('vehicle-selector', 'value'),
            State('trip-selector', 'value'),
            State('simulation-state-store', 'data'),
            prevent_initial_call=True
        )
        def update_simulation_dashboard(n_intervals, vehicle_id, trip_id, sim_state):
            if not vehicle_id or not trip_id or not sim_state:
                return dash.no_update

            trip_df = self.data_handler.get_trip_data(vehicle_id, trip_id)
            if trip_df.empty: return dash.no_update

            duration = len(trip_df)
            trip_distance_km = trip_df['Trip_Distance[m]'].iloc[-1] / 1000.0 if 'Trip_Distance[m]' in trip_df.columns and not trip_df.empty else 0
            
            elapsed_time = n_intervals - sim_state['start_interval']
            
            if duration > 0 and elapsed_time >= duration:
                sim_state['cycle_count'] += 1
                sim_state['total_distance_offset'] += trip_distance_km
                sim_state['start_interval'] = n_intervals
                elapsed_time = 0

            current_index = min(elapsed_time, duration - 1)
            current_data = trip_df.iloc[current_index]
            path_so_far = trip_df.iloc[:current_index + 1]
            
            # --- CREACIÓN DEL OBJETO PATCH ---
            patched_figure = Patch()
            # Actualiza los datos de la línea (traza 0)
            patched_figure['data'][0]['lat'] = path_so_far['Latitude[deg]']
            patched_figure['data'][0]['lon'] = path_so_far['Longitude[deg]']
            # Actualiza los datos del marcador (traza 1)
            patched_figure['data'][1]['lat'] = [current_data['Latitude[deg]']]
            patched_figure['data'][1]['lon'] = [current_data['Longitude[deg]']]
            
            # Cálculo de métricas (sin cambios)
            velocidad = f"{current_data['Vehicle_Speed[km/h]']:.1f} km/h"
            soc = f"{current_data['HV_Battery_SOC[%]']:.1f} %"
            ciclos = f"{sim_state['cycle_count']}"
            distancia_total = sim_state['total_distance_offset'] + (current_data.get('Trip_Distance[m]', 0) / 1000.0)
            total_distance_text = f"{distancia_total:.1f} km"
            mdr_prob = np.interp(distancia_total, self.dist_points, self.prob_points)
            mdr_text = f"{mdr_prob * 100:.1f} %"

            return (patched_figure, velocidad, soc, ciclos, total_distance_text, mdr_text, sim_state)
        
        # Callback para el color de la tarjeta MDR (sin cambios)
        @self.app.callback(
            Output('mdr-card', 'className'),
            Input('text-mdr', 'children')
        )
        def update_mdr_card_color(mdr_text):
            try:
                prob_value = float(mdr_text.replace(' %', ''))
            except (ValueError, TypeError):
                return "mdr-card-base"
            
            if prob_value > 40:
                return "mdr-card-base mdr-red"
            elif prob_value > 20:
                return "mdr-card-base mdr-yellow"
            else:
                return "mdr-card-base mdr-green"
            
    def run(self, debug=True, port=8051):
        self.app.run(debug=debug, port=port)

# Código para Render
DATA_FILEPATH = 'ev_dataset.csv' 
dashboard = DashboardApp(DATA_FILEPATH)
server = dashboard.app.server
if __name__ == '__main__':
    dashboard.run(debug=False)