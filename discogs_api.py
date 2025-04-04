import os
import time
import logging
import pandas as pd
import discogs_client
from dotenv import load_dotenv

# Configurar logging
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

class DiscogsConnector:
    def __init__(self):
        """
        Inicializa el cliente de Discogs usando las credenciales del archivo .env
        Para obtener un token, visita: https://www.discogs.com/settings/developers
        """
        self.token = os.getenv("DISCOGS_TOKEN")
        
        if not self.token:
            logger.warning("No se encontró el token de Discogs en el archivo .env")
            self.client = None
        else:
            try:
                # Crear cliente con User-Agent personalizado para evitar bloqueos
                self.client = discogs_client.Client(
                    'VinylRecommender/1.0',
                    user_token=self.token
                )
                logger.info("Cliente de Discogs inicializado correctamente")
            except Exception as e:
                logger.error(f"Error al inicializar el cliente de Discogs: {e}")
                self.client = None

    def is_ready(self):
        """Verifica si el cliente de Discogs está listo para usarse"""
        return self.client is not None

    def get_release_details(self, release_id):
        """
        Obtiene detalles adicionales de un lanzamiento específico por su ID
        
        Args:
            release_id: ID de lanzamiento de Discogs
            
        Returns:
            dict: Información enriquecida del lanzamiento o None si hay error
        """
        if not self.is_ready() or not release_id:
            return None
            
        try:
            # Convertir a entero si es posible
            if isinstance(release_id, str) and release_id.isdigit():
                release_id = int(release_id)
            elif not isinstance(release_id, int):
                logger.warning(f"ID de lanzamiento no válido: {release_id}")
                return None
                
            # Obtener el lanzamiento de Discogs
            release = self.client.release(release_id)
            
            # Esperar un momento para no exceder los límites de la API
            time.sleep(1)
            
            # Intentar obtener el año original de lanzamiento
            original_year = None
            
            # Primero intentamos obtener el master_id y consultar la versión master para el año original
            master_id = getattr(release, 'master_id', None)
            if master_id:
                try:
                    # Obtener la información del master (versión original)
                    master = self.client.master(master_id)
                    time.sleep(1)  # Esperar para no exceder límites de API
                    original_year = getattr(master, 'year', None)
                    logger.info(f"Año original obtenido del master para {release_id}: {original_year}")
                except Exception as e:
                    logger.warning(f"Error obteniendo master para {release_id}: {e}")
            
            # Si no se pudo obtener del master, intentar con el año del release
            if not original_year:
                original_year = getattr(release, 'year', None)
                logger.info(f"Usando año del release para {release_id}: {original_year}")
            
            # Intentar obtener la valoración de la comunidad si está disponible
            community_rating = None
            if hasattr(release, 'community') and hasattr(release.community, 'rating'):
                try:
                    # Intentar diferentes formas de obtener el rating
                    if hasattr(release.community.rating, 'average'):
                        community_rating = release.community.rating.average
                    elif isinstance(release.community.rating, dict) and 'average' in release.community.rating:
                        community_rating = release.community.rating['average']
                    elif isinstance(release.community.rating, (int, float)):
                        community_rating = release.community.rating
                except:
                    community_rating = None
            
            # Extraer información relevante
            result = {
                'release_id': release_id,
                'original_release_year': original_year,
                'genres': getattr(release, 'genres', []),
                'styles': getattr(release, 'styles', []),
                'tracklist': [{'position': t.position, 'title': t.title, 'duration': t.duration} 
                              for t in getattr(release, 'tracklist', [])],
                'artists': [{'name': a.name, 'id': a.id} for a in getattr(release, 'artists', [])],
                'labels': [{'name': l.name, 'id': l.id} for l in getattr(release, 'labels', [])],
                'images': [],
                'country': getattr(release, 'country', None),
                'community': {
                    'rating': community_rating,
                    'want': getattr(release.community, 'want', None) if hasattr(release, 'community') else None,
                    'have': getattr(release.community, 'have', None) if hasattr(release, 'community') else None
                }
            }
            
            # Procesar imágenes correctamente
            if hasattr(release, 'images'):
                for img in release.images:
                    image_data = {}
                    if hasattr(img, 'uri'):
                        image_data['uri'] = img.uri
                    if hasattr(img, 'type'):
                        image_data['type'] = img.type
                    if image_data:  # Solo añadir si se obtuvo algún dato
                        result['images'].append(image_data)
            
            logger.info(f"Detalles obtenidos para el lanzamiento {release_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo detalles del lanzamiento {release_id}: {e}")
            return None

    def enrich_collection(self, collection_df):
        """
        Enriquece la información de toda la colección con datos adicionales de Discogs
        
        Args:
            collection_df: DataFrame de pandas con la colección (debe tener columna 'release_id')
            
        Returns:
            DataFrame: DataFrame enriquecido con información adicional
        """
        if not self.is_ready():
            logger.error("El cliente de Discogs no está inicializado. Verifica tu token.")
            return collection_df
        
        # Verificar que exista la columna release_id    
        if 'release_id' not in collection_df.columns:
            logger.warning("La columna 'release_id' no existe en el DataFrame")
            return collection_df
            
        # Crear copia del DataFrame original
        enriched_df = collection_df.copy()
        
        # Columnas para almacenar la información adicional
        enriched_df['original_release_year'] = None
        enriched_df['community_rating'] = None
        enriched_df['tracklist'] = None
        enriched_df['image_url'] = None
        
        # Contador para mostrar progreso
        total_releases = len(enriched_df)
        logger.info(f"Comenzando a enriquecer {total_releases} lanzamientos...")
        
        # Para cada lanzamiento, obtener información adicional
        for idx, row in enriched_df.iterrows():
            release_id = row['release_id']
            
            # Mostrar progreso
            if idx % 10 == 0:
                logger.info(f"Procesando lanzamiento {idx+1} de {total_releases}")
                
            # Obtener detalles y actualizar el DataFrame
            details = self.get_release_details(release_id)
            if details:
                enriched_df.at[idx, 'original_release_year'] = details['original_release_year']
                enriched_df.at[idx, 'community_rating'] = details['community']['rating']
                
                # Guardar la primera imagen de tipo 'primary' o 'secondary' si existe
                images = details.get('images', [])
                primary_images = [img for img in images if img.get('type') in ('primary', 'secondary')]
                
                if primary_images:
                    enriched_df.at[idx, 'image_url'] = primary_images[0]['uri']
                
                # Convertir la tracklist a una cadena resumida
                tracklist = details.get('tracklist', [])
                if tracklist:
                    tracks_summary = '; '.join([f"{t['position']}. {t['title']}" for t in tracklist[:5]])
                    if len(tracklist) > 5:
                        tracks_summary += f"; ... (+{len(tracklist)-5} más)"
                    enriched_df.at[idx, 'tracklist'] = tracks_summary
        
        logger.info(f"Proceso de enriquecimiento completado para {total_releases} lanzamientos")
        return enriched_df

# Función de utilidad para guardar la colección enriquecida
def save_enriched_collection(enriched_df, output_path='data/enriched_collection.csv'):
    """Guarda la colección enriquecida en un nuevo archivo CSV"""
    try:
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Guardar a CSV
        enriched_df.to_csv(output_path, index=False)
        logger.info(f"Colección enriquecida guardada en {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error guardando la colección enriquecida: {e}")
        return False

# Función para cargar y enriquecer una colección desde un archivo CSV
def enrich_collection_from_file(input_csv_path, output_csv_path=None):
    """
    Carga un archivo CSV de colección de Discogs y lo enriquece con datos adicionales
    
    Args:
        input_csv_path: Ruta al archivo CSV de la colección
        output_csv_path: Ruta para guardar el archivo enriquecido (opcional)
        
    Returns:
        DataFrame: DataFrame con la colección enriquecida
    """
    try:
        # Cargar el CSV original
        df = pd.read_csv(input_csv_path)
        logger.info(f"CSV cargado correctamente: {len(df)} registros")
        
        # Inicializar conector de Discogs
        connector = DiscogsConnector()
        
        if not connector.is_ready():
            logger.error("No se pudo inicializar el conector de Discogs")
            return df
            
        # Enriquecer la colección
        enriched_df = connector.enrich_collection(df)
        
        # Guardar a CSV si se especificó una ruta
        if output_csv_path:
            save_enriched_collection(enriched_df, output_csv_path)
            
        return enriched_df
    except Exception as e:
        logger.error(f"Error en el proceso de enriquecimiento: {e}")
        return None

if __name__ == "__main__":
    # Configuración de logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ejemplo de uso
    input_path = 'data/vinyl_collection.csv'
    output_path = 'data/enriched_collection.csv'
    
    if os.path.exists(input_path):
        logger.info(f"Iniciando enriquecimiento de {input_path}")
        
        # Prueba rápida: solo cargar y enriquecer los primeros 10 discos
        df = pd.read_csv(input_path)
        logger.info(f"CSV cargado correctamente: {len(df)} registros")
        logger.info(f"Para pruebas, solo se enriquecerán los primeros 10 registros")
        
        # Inicializar conector de Discogs
        connector = DiscogsConnector()
        
        if not connector.is_ready():
            logger.error("No se pudo inicializar el conector de Discogs")
        else:
            # Enriquecer la colección limitada
            enriched_df = connector.enrich_collection(df)
            
            # Combinar con los datos originales
            # Copiar los primeros 10 registros enriquecidos
            for idx in range(len(df)):
                df.loc[idx, 'original_release_year'] = enriched_df.loc[idx, 'original_release_year']
                df.loc[idx, 'community_rating'] = enriched_df.loc[idx, 'community_rating']
                df.loc[idx, 'tracklist'] = enriched_df.loc[idx, 'tracklist']
                df.loc[idx, 'image_url'] = enriched_df.loc[idx, 'image_url']
            
            # Guardar todo el dataframe (con solo los primeros 10 enriquecidos)
            save_enriched_collection(df, output_path)
            logger.info(f"Proceso completado. Se han enriquecido {len(df)} registros.")
    else:
        logger.error(f"El archivo {input_path} no existe") 