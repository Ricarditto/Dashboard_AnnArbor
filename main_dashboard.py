import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import numpy as np # Necesario para la interpolación

from data_handler import DataHandler

class DashboardApp:
    def __init__(self, data_filepath):
        self.data_handler = DataHandler(data_filepath)
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        self.app.title = "EV Degradation Simulator"
        self.trip_color = '#BB86FC'
        
        # --- Datos de la Distribución del PDF ---
        # Distancias en km y sus probabilidades acumuladas correspondientes
        self.dist_points = np.array([0, 60, 65, 70, 75, 80, 85, 90, 95, 100, 110])
        self.prob_points = np.array([0, 0, 0.05, 0.15, 0.3, 0.4, 0.55, 0.7, 0.88, 1.0, 1.0])

        self.app.layout = self._create_layout()
        self._register_callbacks()

    def _create_layout(self):
        all_vehicles = self.data_handler.get_all_vehicles()
        default_vehicle_id = 455
        default_trip_id = 2323
        default_trip_options = [{'label': f'Trip {default_trip_id}', 'value': default_trip_id}]

        dcc.Interval(
            id='interval-component',
            interval=3000,  # <-- 3000ms = 3 segundos por punto
            n_intervals=0
        ),

        stores = [
            dcc.Store(id='simulation-state-store', data={
                'cycle_count': 0, 'total_distance_offset': 0.0, 'start_interval': 0
            })
        ]

        control_panel = html.Div(className="selector-slot", children=[
            html.H3("Simulation Control"),
            html.Label("Vehicle:"),
            dcc.Dropdown(id='vehicle-selector', value=default_vehicle_id, clearable=False, disabled=True),
            html.Label("Trip:"),
            dcc.Dropdown(id='trip-selector', options=default_trip_options, value=default_trip_id, clearable=False, disabled=True)
        ])

        metrics_sidebar = html.Div(className="metrics-sidebar", children=[
            html.H3("Live Trip Metrics", style={'color': self.trip_color}),
            html.Div(className="metric-card", children=[html.H2("Speed"), html.P(id="text-velocidad", children="-- km/h")]),
            html.Div(className="metric-card", children=[html.H2("State of Charge (SOC)"), html.P(id="text-soc", children="-- %")]),
            html.H3("Cumulative Simulation", style={'color': '#03DAC6', 'marginTop': '20px'}),
            html.Div(className="metric-card", children=[html.H2("Cycle Count"), html.P(id="text-cycle-count", children="0")]),
            html.Div(className="metric-card", children=[html.H2("Total Distance"), html.P(id="text-total-distance", children="0.0 km")]),
            # Damos un ID a la tarjeta de MDR para poder cambiar su clase (color)
            html.Div(id="mdr-card", className="mdr-card-base", children=[html.H2("MDR (Probability)"), html.P(id="text-mdr", children="0.0 %")]),
        ])

        return html.Div(className="dashboard-container", children=[
            *stores,
            dcc.Interval(id='interval-component', interval=100, n_intervals=0), # Simulación más rápida
            html.Header(className="main-header", children=[html.H1("🛰️ Repetitive Trip Simulator")]),
            html.Div(className="control-panel-multi", style={'gridTemplateColumns': '1fr'}, children=[control_panel]),
            html.Main(className="main-content-dual-metrics", children=[
                metrics_sidebar,
                html.Div(className="map-container-dual-metrics", children=[dcc.Graph(id='vehicle-map', style={'height': '100%'})]),
            ])
        ])

    def _register_callbacks(self):
        @self.app.callback(
            Output('simulation-state-store', 'data'),
            Input('trip-selector', 'value'), # Se activa si cambia el viaje
            State('interval-component', 'n_intervals')
        )
        def reset_simulation(trip_id, n_intervals):
            return {'cycle_count': 0, 'total_distance_offset': 0.0, 'start_interval': n_intervals}

        @self.app.callback(
            Output('vehicle-map', 'figure'),
            Output('text-velocidad', 'children'), Output('text-soc', 'children'),
            Output('text-cycle-count', 'children'), Output('text-total-distance', 'children'),
            Output('text-mdr', 'children'),
            Output('simulation-state-store', 'data', allow_duplicate=True),
            Input('interval-component', 'n_intervals'),
            State('vehicle-selector', 'value'), State('trip-selector', 'value'),
            State('simulation-state-store', 'data'),
            prevent_initial_call=True
        )
        def update_simulation_dashboard(n_intervals, vehicle_id, trip_id, sim_state):
            if not vehicle_id or not trip_id or not sim_state:
                return dash.no_update

            trip_df = self.data_handler.get_trip_data(vehicle_id, trip_id)
            if trip_df.empty: return dash.no_update

            duration = len(trip_df)
            trip_distance_km = trip_df['Trip_Distance[m]'].iloc[-1] / 1000.0
            
            elapsed_time = n_intervals - sim_state['start_interval']
            
            if elapsed_time >= duration:
                sim_state['cycle_count'] += 1
                sim_state['total_distance_offset'] += trip_distance_km
                sim_state['start_interval'] = n_intervals
                elapsed_time = 0

            current_index = elapsed_time
            current_data = trip_df.iloc[current_index]
            path_so_far = trip_df.iloc[:current_index + 1]
            
            # --- Cálculos de Métricas ---
            velocidad = f"{current_data['Vehicle_Speed[km/h]']:.1f} km/h"
            soc = f"{current_data['HV_Battery_SOC[%]']:.1f} %"
            
            ciclos = f"{sim_state['cycle_count']}"
            distancia_viaje_actual_km = (current_data['Trip_Distance[m]'] / 1000.0)
            distancia_total = sim_state['total_distance_offset'] + distancia_viaje_actual_km
            total_distance_text = f"{distancia_total:.1f} km"
            
            # --- Lógica de Probabilidad MDR ---
            # Interpolar para encontrar la probabilidad basada en la distancia total
            mdr_prob = np.interp(distancia_total, self.dist_points, self.prob_points)
            mdr_text = f"{mdr_prob * 100:.1f} %"
            
            # --- Actualización del Mapa ---
            fig = go.Figure()
            fig.update_layout(
                mapbox_style="open-street-map",
                mapbox_center=dict(lat=42.2850, lon=-83.7380),
                mapbox_zoom=12.5,
                margin={"r":0, "t":0, "l":0, "b":0},
                showlegend=False
            )
            fig.add_trace(go.Scattermapbox(
                lat=path_so_far['Latitude[deg]'], lon=path_so_far['Longitude[deg]'],
                mode='lines', line=dict(color=self.trip_color, width=3)
            ))
            fig.add_trace(go.Scattermapbox(
                lat=[current_data['Latitude[deg]']], lon=[current_data['Longitude[deg]']],
                mode='markers', marker=dict(size=15, color=self.trip_color)
            ))

            return (fig, velocidad, soc, ciclos, total_distance_text, mdr_text, sim_state)
        
        @self.app.callback(
            Output('mdr-card', 'className'),
            Input('text-mdr', 'children')
        )
        def update_mdr_card_color(mdr_text):
            try:
                # Extraer el valor numérico del texto
                prob_value = float(mdr_text.replace(' %', ''))
            except (ValueError, TypeError):
                return "mdr-card-base" # Color por defecto
            
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