import pandas as pd

class DataHandler:
    """
    Una clase para manejar la carga, procesamiento y consulta
    de los datos de telemetría de los vehículos.
    """
    def __init__(self, filepath):
        """
        Constructor de la clase. Carga y prepara los datos del archivo CSV.
        
        Args:
            filepath (str): La ruta al archivo CSV de datos.
        """
        self.filepath = filepath
        self.df = self._load_and_prepare_data()

    def _load_and_prepare_data(self):
        """
        Método privado para cargar el CSV y realizar la limpieza inicial.
        """
        print("Cargando y preparando los datos. Esto puede tardar un momento...")
        
        # Cargar el archivo CSV
        df = pd.read_csv(self.filepath, low_memory=False)
        
        # Convertir la columna de timestamp a un formato de fecha y hora usable
        # Usamos 'coerce' para convertir errores en NaT (Not a Time)
        df['Timestamp'] = pd.to_datetime(df['Timestamp(ms)'], unit='ms', errors='coerce')
        
        # Eliminar filas donde el timestamp no sea válido
        df.dropna(subset=['Timestamp'], inplace=True)
        
        # Ordenar todo el dataframe por tiempo. Es crucial para las simulaciones.
        df.sort_values('Timestamp', inplace=True)
        
        print("¡Datos cargados y listos!")
        return df

    def get_trip_data(self, vehicle_id, trip_id):
        """
        Filtra y devuelve los datos para un vehículo y viaje específicos.
        
        Args:
            vehicle_id (int): El ID del vehículo.
            trip_id (int): El ID del viaje.
            
        Returns:
            pandas.DataFrame: Un DataFrame que contiene solo los datos del viaje solicitado.
        """
        if self.df is None:
            return pd.DataFrame() # Devuelve un DataFrame vacío si los datos no se cargaron
            
        trip_df = self.df[
            (self.df['VehId'] == vehicle_id) & 
            (self.df['Trip'] == trip_id)
        ].copy() # Usamos .copy() para evitar warnings de Pandas
        
        return trip_df.reset_index(drop=True)

    def get_all_vehicles(self):
        """
        Devuelve una lista ordenada de todos los IDs de vehículos únicos.
        """
        return sorted(self.df['VehId'].unique())

    def get_trips_for_vehicle(self, vehicle_id):
        """
        Devuelve una lista ordenada de todos los IDs de viajes únicos para un vehículo.
        """
        if vehicle_id is None:
            return []
        
        trips = self.df[self.df['VehId'] == vehicle_id]['Trip'].unique()
        return sorted(trips)