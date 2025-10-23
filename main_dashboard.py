import dash
from dash import dcc, html, Input, Output, State, Patch
from dash.exceptions import PreventUpdate
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
        
        self.dist_points = np.array([0, 70 ,75, 80, 87, 90, 93, 95, 98, 100, 103])
        self.prob_points = np.array([0, 0, 0.05, 0.15, 0.3, 0.4, 0.55, 0.7, 0.88, 0.96, 0.98])

        self.app.layout = self._create_layout()
        self._register_callbacks()

    def _create_layout(self):
        all_vehicles = self.data_handler.get_all_vehicles()
        default_vehicle_id = 455
        default_trip_id = 2323
        default_trip_options = [{'label': f'Trip {default_trip_id}', 'value': default_trip_id}]

        stores = [
            dcc.Store(id='simulation-state-store', data={
                'cycle_count': 0, 
                'total_distance_offset': 0.0, 
                'start_interval': 0,
                'soc_offset': 0.0,
                'direction': 'forward'
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
            html.Div(id="mdr-card", className="metric-card", children=[html.H2("MDR (Probability)"), html.P(id="text-mdr", children="0.0 %")]),
        ])

        return html.Div(className="dashboard-container", children=[
            *stores,
            dcc.Interval(id='interval-component', interval=50, n_intervals=0),
            html.Header(className="main-header", children=[html.H1("🛰️EV-Sim Dashboard")]),
            html.Div(className="control-panel-multi", style={'gridTemplateColumns': '1fr'}, children=[control_panel]),
            html.Main(className="main-content-dual-metrics", children=[
                metrics_sidebar,
                html.Div(className="map-container-dual-metrics", children=[dcc.Graph(id='vehicle-map', style={'height': '100%'})]),
            ])
        ])

    def _register_callbacks(self):
        @self.app.callback(
            Output('trip-selector', 'options'),
            Output('trip-selector', 'value'),
            Input('vehicle-selector', 'value'),
            prevent_initial_call=True
        )
        def update_trip_options(selected_vehicle):
            if selected_vehicle is None: 
                raise PreventUpdate
            trips = self.data_handler.get_trips_for_vehicle(selected_vehicle)
            options = [{'label': f'Trip {int(trip)}', 'value': trip} for trip in trips]
            return options, trips[0] if trips else None

        @self.app.callback(
            Output('vehicle-map', 'figure'),
            Output('simulation-state-store', 'data'),
            Output('interval-component', 'disabled'),
            Output('text-velocidad', 'children'),
            Output('text-soc', 'children'),
            Output('text-cycle-count', 'children'),
            Output('text-total-distance', 'children'),
            Output('text-mdr', 'children'),
            Input('interval-component', 'n_intervals'),
            Input('trip-selector', 'value'),
            State('vehicle-selector', 'value'),
            State('simulation-state-store', 'data'),
        )
        def unified_simulation_callback(n_intervals, trip_id, vehicle_id, sim_state):
            ctx = dash.callback_context
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'initial_load'

            if not vehicle_id or not trip_id:
                raise PreventUpdate

            if trigger_id == 'trip-selector' or trigger_id == 'initial_load':
                sim_state = {'cycle_count': 0, 'total_distance_offset': 0.0, 'start_interval': n_intervals, 'soc_offset': 0.0, 'direction': 'forward'}

            trip_df = self.data_handler.get_trip_data(vehicle_id, trip_id)
            if trip_df.empty: 
                raise PreventUpdate

            duration = len(trip_df)
            trip_distance_m = trip_df['Trip_Distance[m]'].iloc[-1] if 'Trip_Distance[m]' in trip_df.columns else 0
            soc_inicial_viaje = trip_df['HV_Battery_SOC[%]'].iloc[0]
            soc_final_viaje = trip_df['HV_Battery_SOC[%]'].iloc[-1]
            soc_consumido_por_viaje = soc_inicial_viaje - soc_final_viaje
            
            elapsed_time = n_intervals - sim_state['start_interval']
            
            if duration > 0 and elapsed_time >= duration:
                # --- ACUMULACIÓN CORRECTA: Se actualiza al final de CADA tramo (ida o vuelta) ---
                sim_state['total_distance_offset'] += (trip_distance_m / 1000.0)
                sim_state['soc_offset'] += soc_consumido_por_viaje
                
                if sim_state['direction'] == 'forward':
                    sim_state['direction'] = 'backward'
                else:
                    sim_state['direction'] = 'forward'
                    sim_state['cycle_count'] += 1 # Un ciclo se cuenta al completar la vuelta
                
                sim_state['start_interval'] = n_intervals
                elapsed_time = 0

            # --- Lógica de Posición (sin cambios) ---
            if sim_state['direction'] == 'forward':
                current_index = min(elapsed_time, duration - 1)
            else:
                current_index = max(0, duration - 1 - elapsed_time)
            
            current_data = trip_df.iloc[current_index]
            
            # --- CÁLCULO DE MÉTRICAS SIMPLIFICADO Y CORREGIDO ---
            # El SOC y la Distancia del tramo actual se calculan de forma simétrica
            if sim_state['direction'] == 'forward':
                distance_this_leg_km = current_data.get('Trip_Distance[m]', 0) / 1000.0
                soc_actual = current_data['HV_Battery_SOC[%]'] - sim_state['soc_offset']
            else: # backward
                distance_this_leg_km = (trip_distance_m - current_data.get('Trip_Distance[m]', 0)) / 1000.0
                apparent_soc_regen = current_data['HV_Battery_SOC[%]'] - soc_final_viaje
                soc_at_turnaround = soc_final_viaje - (sim_state['soc_offset'] - soc_consumido_por_viaje)
                soc_actual = soc_at_turnaround - apparent_soc_regen

            # El total es siempre el offset + el progreso en el tramo actual
            distancia_total = sim_state['total_distance_offset'] + distance_this_leg_km
            # --- FIN DE LA CORRECCIÓN ---

            disable_interval = soc_actual <= 0
            if soc_actual <= 0: soc_actual = 0
            
            path_so_far = trip_df.iloc[:current_index + 1] if sim_state['direction'] == 'forward' else trip_df.iloc[current_index:]
            
            velocidad = f"{current_data['Vehicle_Speed[km/h]']:.1f} km/h"
            soc = f"{soc_actual:.1f} %"
            ciclos = f"{sim_state['cycle_count']}"
            total_distance_text = f"{distancia_total:.1f} km"
            mdr_prob = np.interp(distancia_total, self.dist_points, self.prob_points)
            mdr_text = f"{mdr_prob * 100:.1f} %"
            
            if trigger_id == 'trip-selector' or trigger_id == 'initial_load':
                fig = go.Figure()
                fig.add_trace(go.Scattermap(lat=[], lon=[], mode='lines', line=dict(color=self.trip_color, width=3)))
                fig.add_trace(go.Scattermap(lat=[current_data['Latitude[deg]']], lon=[current_data['Longitude[deg]']], 
                                            mode='markers', marker=dict(symbol='car', size=30, color='black')))
                fig.update_layout(
                    margin={"r":0, "t":0, "l":0, "b":0}, showlegend=False,
                    map_style="open-street-map",
                    map_center=dict(lat=42.2850, lon=-83.7380), map_zoom=12.5
                )
                return fig, sim_state, disable_interval, velocidad, soc, ciclos, total_distance_text, mdr_text
            else:
                patched_figure = Patch()
                patched_figure['data'][0]['lat'] = path_so_far['Latitude[deg]']
                patched_figure['data'][0]['lon'] = path_so_far['Longitude[deg]']
                patched_figure['data'][1]['lat'] = [current_data['Latitude[deg]']]
                patched_figure['data'][1]['lon'] = [current_data['Longitude[deg]']]
                return patched_figure, sim_state, disable_interval, velocidad, soc, ciclos, total_distance_text, mdr_text
        
        @self.app.callback(
            Output('mdr-card', 'className'),
            Input('text-mdr', 'children')
        )
        def update_mdr_card_color(mdr_text):
            try:
                prob_value = float(mdr_text.replace(' %', ''))
            except (ValueError, TypeError):
                return "metric-card"
            
            if prob_value > 40:
                return "metric-card mdr-red"
            elif prob_value > 20:
                return "metric-card mdr-yellow"
            else:
                return "metric-card mdr-green"
            
    def run(self, debug=True, port=8051):
        self.app.run(debug=debug, port=port)

# Código para Render
DATA_FILEPATH = 'ev_dataset.csv' 
dashboard = DashboardApp(DATA_FILEPATH)
server = dashboard.app.server
if __name__ == '__main__':
    dashboard.run(debug=False)