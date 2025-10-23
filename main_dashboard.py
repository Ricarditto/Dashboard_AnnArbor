import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import math # <--- AÑADIDO

# Asumiendo que data_handler.py existe y la clase DataHandler está definida
# Se crea una clase placeholder si no se proporciona el archivo
try:
    from data_handler import DataHandler
except ImportError:
    print("Advertencia: No se encontró data_handler.py. Usando DataHandler placeholder.")
    class DataHandler:
        def __init__(self, filepath):
            # Simulación simple: Cargar datos y asumir columnas
            try:
                self.df = pd.read_csv(filepath)
                # Asegurarse de que las columnas necesarias existan (simulación)
                if 'Vehicle_ID' not in self.df: self.df['Vehicle_ID'] = 455
                if 'Trip_ID' not in self.df: self.df['Trip_ID'] = 1197
                if 'Latitude[deg]' not in self.df: self.df['Latitude[deg]'] = 42.28
                if 'Longitude[deg]' not in self.df: self.df['Longitude[deg]'] = -83.73
                if 'Vehicle_Speed[km/h]' not in self.df: self.df['Vehicle_Speed[km/h]'] = 0
                if 'HV_Battery_SOC[%]' not in self.df: self.df['HV_Battery_SOC[%]'] = 100
                if 'HV_Battery_Voltage[V]' not in self.df: self.df['HV_Battery_Voltage[V]'] = 400
                if 'Power[W]' not in self.df: self.df['Power[W]'] = 0
                if 'Accum_Energy[kWh]' not in self.df: self.df['Accum_Energy[kWh]'] = 0

            except FileNotFoundError:
                print(f"Error: No se encontró el archivo de datos en {filepath}")
                self.df = pd.DataFrame()
            except Exception as e:
                print(f"Error cargando datos: {e}")
                self.df = pd.DataFrame()


        def get_all_vehicles(self):
            if 'Vehicle_ID' in self.df:
                return self.df['Vehicle_ID'].unique()
            return [455] # Valor predeterminado

        def get_trips_for_vehicle(self, vehicle_id):
            if 'Vehicle_ID' in self.df and 'Trip_ID' in self.df:
                return self.df[self.df['Vehicle_ID'] == vehicle_id]['Trip_ID'].unique()
            return [1197, 1648] # Valores predeterminados

        def get_trip_data(self, vehicle_id, trip_id):
            if self.df.empty:
                return pd.DataFrame()
            
            trip_df = self.df[
                (self.df['Vehicle_ID'] == vehicle_id) & 
                (self.df['Trip_ID'] == trip_id)
            ].copy()
            
            # Asegurar que los datos estén ordenados (simulación, idealmente por timestamp)
            # Aquí se asume que el CSV ya está ordenado por tiempo para ese viaje
            return trip_df.reset_index(drop=True)


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

        stores = [dcc.Store(id='cycle-start-store')]
        
        control_slots = []
        for i in range(1, 3):
            slot = html.Div(className="selector-slot", children=[
                html.H3(f"Vehicle {i} Selection", style={'color': self.trip_colors[i-1]}),
                html.Label("Select Vehicle:"),
                dcc.Dropdown(
                    id=f'vehicle-selector-{i}',
                    options=[{'label': f'Vehicle {v}', 'value': v} for v in all_vehicles],
                    value=455,
                    className="vehicle-dropdown"
                ),
                html.Label("Select Trip:"),
                dcc.Dropdown(
                    id=f'trip-selector-{i}',
                    options=default_trip_options,
                    value=1197 if i == 1 else 1648,
                    className="trip-dropdown"
                )
            ])
            control_slots.append(slot)

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
            *stores,
            # Se mueve el dcc.Interval aquí para que esté en el layout
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

        for i in range(1, 3):
            create_callback_functions(i)

        @self.app.callback(
            Output('cycle-start-store', 'data'),
            Input('trip-selector-1', 'value'),
            Input('trip-selector-2', 'value'),
            State('interval-component', 'n_intervals')
        )
        def reset_simulation_cycle(trip1, trip2, n_intervals):
            # Resetea el contador de inicio cada vez que se cambia un viaje
            return n_intervals

        @self.app.callback(
            Output('vehicle-map', 'figure'),
            Output('text-velocidad-1', 'children'), Output('text-soc-1', 'children'), Output('text-voltaje-1', 'children'),
            Output('text-potencia-1', 'children'), Output('text-energia-1', 'children'), Output('text-degradation-1', 'children'),
            Output('text-mdr-1', 'children'),
            Output('text-velocidad-2', 'children'), Output('text-soc-2', 'children'), Output('text-voltaje-2', 'children'),
            Output('text-potencia-2', 'children'), Output('text-energia-2', 'children'), Output('text-degradation-2', 'children'),
            Output('text-mdr-2', 'children'),
            Input('interval-component', 'n_intervals'),
            State('vehicle-selector-1', 'value'), State('vehicle-selector-2', 'value'),
            State('trip-selector-1', 'value'), State('trip-selector-2', 'value'),
            State('cycle-start-store', 'data'),
        )
        def update_multi_trip_dashboard(n_intervals, 
                                        vehicle_id_1, vehicle_id_2,
                                        trip_id_1, trip_id_2,
                                        cycle_start_interval):
            
            vehicle_ids = [vehicle_id_1, vehicle_id_2]
            trip_ids = [trip_id_1, trip_id_2]
            
            fig = go.Figure()
            
            fig.update_layout(
                map_style="open-street-map",
                map_center=dict(lat=42.2850, lon=-83.7380), # Coordenadas centradas en Ann Arbor
                map_zoom=11.5,
                margin={"r":0, "t":0, "l":0, "b":0},
                showlegend=False
            )
            
            metrics_outputs = ["-- km/h", "-- %", "-- V", "-- kW", "-- kWh", "--", "--"] * 2
            
            trip_dfs = [self.data_handler.get_trip_data(vid, tid) for vid, tid in zip(vehicle_ids, trip_ids)]
            durations = [len(df) for df in trip_dfs]
            max_duration = max(durations) if any(d for d in durations if d > 0) else 0

            # ----- INICIO DE LA MODIFICACIÓN (Aceleración) -----
            TARGET_SIMULATION_SECONDS = 40.0 # 40 segundos
            # Debe coincidir con dcc.Interval en _create_layout
            INTERVAL_MS = 500.0 
            
            # Total de "ticks" que debe durar la simulación
            total_ticks_for_sim = (TARGET_SIMULATION_SECONDS * 1000) / INTERVAL_MS
            
            # Cuántos puntos de datos saltar en cada "tick"
            # Usamos max(1, ...) para evitar step_size = 0 si max_duration es muy pequeño
            step_size = 1 
            if max_duration > 0 and total_ticks_for_sim > 0:
                step_size = max(1, int(math.ceil(max_duration / total_ticks_for_sim)))

            if cycle_start_interval is None or max_duration == 0:
                current_data_index = 0
            else:
                elapsed_ticks = n_intervals - cycle_start_interval
                # Calcular el índice de datos actual basado en los ticks y el step_size
                current_data_index = (elapsed_ticks * step_size)
            
            # Asegurarse de que el ciclo se repita (módulo)
            if max_duration > 0:
                current_data_index = current_data_index % max_duration
            else:
                current_data_index = 0
            # ----- FIN DE LA MODIFICACIÓN -----

            for i in range(2):
                trip_df = trip_dfs[i]
                duration = durations[i]

                if not trip_df.empty:
                    # ----- MODIFICACIÓN DE ÍNDICE -----
                    # Ajustar el índice para el ciclo actual de este viaje específico
                    # Usamos el nuevo 'current_data_index'
                    current_index = min(current_data_index, duration - 1) if duration > 0 else 0
                    # ----- FIN MODIFICACIÓN DE ÍNDICE -----
                    
                    if duration == 0:
                        continue # No hay datos para este viaje

                    current_data = trip_df.iloc[current_index]
                    path_so_far = trip_df.iloc[:current_index + 1]

                    # ----- INICIO DE LA MODIFICACIÓN -----
                    # Trazo de la ruta (línea) - Se añade 'below=""'
                    fig.add_trace(go.Scattermap(
                        lat=path_so_far['Latitude[deg]'], lon=path_so_far['Longitude[deg]'],
                        mode='lines', line=dict(color=self.trip_colors[i], width=3),
                        below='' # Forzar que se dibuje encima de las capas del mapa
                    ))
                    # ----- FIN DE LA MODIFICACIÓN -----


                    # ----- INICIO DE LA MODIFICACIÓN -----
                    # Icono de auto - Se vuelve a 'markers' con 'symbol="car"'
                    # Se añade 'below=""' para forzar que se dibuje encima de todo.
                    fig.add_trace(go.Scattermap(
                       lat=[current_data['Latitude[deg]']], lon=[current_data['Longitude[deg]']],
                       mode='markers',
                       marker=dict(
                           size=20,
                           symbol='car',
                           color=self.trip_colors[i],
                           allowoverlap=True # Permitir superposición
                       ),
                       below='' # Forzar que se dibuje encima de todo
                    ))
                    # ----- FIN DE LA MODIFICACIÓN -----


                    metrics_start_index = i * 7
                    metrics_outputs[metrics_start_index] = f"{current_data['Vehicle_Speed[km/h]']:.1f} km/h"
                    metrics_outputs[metrics_start_index + 1] = f"{current_data['HV_Battery_SOC[%]']:.1f} %"
                    metrics_outputs[metrics_start_index + 2] = f"{current_data['HV_Battery_Voltage[V]']:.1f} V"
                    metrics_outputs[metrics_start_index + 3] = f"{current_data['Power[W]'] / 1000:.2f} kW"
                    metrics_outputs[metrics_start_index + 4] = f"{current_data['Accum_Energy[kWh]']:.3f} kWh"
                    # Asumiendo que MDR y Degradation no están en el CSV, se dejan como placeholder
                    metrics_outputs[metrics_start_index + 5] = "--" # MDR
                    metrics_outputs[metrics_start_index + 6] = "--" # Degradation

            return [fig] + metrics_outputs
        
    def run(self, debug=True, port=8051):
        self.app.run(debug=debug, port=port)

# Código para Render
DATA_FILEPATH = 'ev_dataset.csv' 
dashboard = DashboardApp(DATA_FILEPATH)
server = dashboard.app.server
if __name__ == '__main__':
    dashboard.run(debug=False)
