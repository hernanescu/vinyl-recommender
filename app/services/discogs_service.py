import os
import time
import logging
import pandas as pd
import discogs_client
import requests
from app.config import DISCOGS_TOKEN, COLLECTION_CSV_PATH, ENRICHED_COLLECTION_PATH, DATA_DIR

logger = logging.getLogger(__name__)

class DiscogsConnector:
    def __init__(self, token=None):
        """
        Inicializa el cliente de Discogs usando las credenciales del archivo .env
        o un token proporcionado
        
        Args:
            token: Token opcional para sobrescribir el configurado
        """
        self.token = token if token else DISCOGS_TOKEN
        
        if not self.token:
            logger.warning("No se encontró el token de Discogs")
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

    def get_user_collection(self, username):
        """
        Obtiene la colección de vinilos de un usuario de Discogs
        
        Args:
            username: Nombre de usuario de Discogs
            
        Returns:
            DataFrame: DataFrame con la colección del usuario
        """
        if not self.is_ready():
            logger.error("El cliente de Discogs no está inicializado")
            return None
            
        try:
            # Obtener el usuario
            user = self.client.user(username)
            if not user:
                logger.error(f"No se encontró el usuario {username}")
                return None
                
            # Obtener la colección (esto devolverá todos los items en la colección)
            collection = user.collection_folders[0].releases
            
            # Crear lista para almacenar los datos
            releases = []
            
            # Iterar por los lanzamientos (con paginación)
            page = 1
            max_page_errors = 0  # Contador de errores de paginación
            
            logger.info(f"Comenzando a obtener colección del usuario {username}")
            
            while max_page_errors < 2:  # Si tenemos 2 errores consecutivos, asumimos que llegamos al final
                try:
                    # En versiones recientes de discogs_client, page() no acepta per_page
                    # Intentamos primero con el método estándar
                    try:
                        items = collection.page(page)
                        if not items:
                            logger.info(f"No hay más elementos en la página {page}")
                            break
                            
                        # Mostrar progreso
                        logger.info(f"Obteniendo página {page} de la colección de {username} - {len(items)} elementos")
                        
                        # Reiniciar contador de errores ya que obtuvimos una página válida
                        max_page_errors = 0
                    except Exception as e:
                        # Si el error indica que estamos fuera del rango de páginas, salimos del bucle
                        error_str = str(e).lower()
                        if "outside of valid range" in error_str or "page not found" in error_str or "404" in error_str:
                            logger.info(f"Llegamos al final de las páginas disponibles: {e}")
                            break
                            
                        logger.warning(f"Error con el método de paginación estándar: {e}")
                        max_page_errors += 1
                        
                        # Si es el primer error, intentar obtener toda la colección de una vez
                        if max_page_errors == 1:
                            try:
                                items = list(collection)
                                logger.info(f"Obteniendo colección completa de {username} (sin paginación)")
                                
                                # Procesar toda la colección y salir del bucle
                                for item in items:
                                    try:
                                        # Obtener datos básicos
                                        artist_name = "Unknown"
                                        if hasattr(item.release, 'artists') and item.release.artists:
                                            artist_name = item.release.artists[0].name
                                            
                                        label_name = ""
                                        if hasattr(item.release, 'labels') and item.release.labels:
                                            label_name = item.release.labels[0].name
                                            
                                        formats = ""
                                        if hasattr(item.release, 'formats'):
                                            formats = ', '.join(f.name for f in item.release.formats if hasattr(f, 'name'))
                                            
                                        # Crear diccionario con los datos
                                        release_data = {
                                            'release_id': item.release.id,
                                            'Artist': artist_name,
                                            'Title': item.release.title,
                                            'Label': label_name,
                                            'Format': formats,
                                            'Released': getattr(item.release, 'year', ''),
                                            'Genre': ', '.join(getattr(item.release, 'genres', [])),
                                            'Style': ', '.join(getattr(item.release, 'styles', [])),
                                            'Rating': getattr(item, 'rating', ''),
                                            'Collection Media Condition': getattr(item, 'media_condition', ''),
                                            'Collection Sleeve Condition': getattr(item, 'sleeve_condition', '')
                                        }
                                        releases.append(release_data)
                                    except Exception as item_e:
                                        logger.warning(f"Error procesando item: {item_e}")
                                        continue
                                
                                # Salir del bucle after processing all items
                                break
                            except Exception as inner_e:
                                logger.error(f"No se pudo obtener la colección completa: {inner_e}")
                                max_page_errors += 1
                                time.sleep(1)  # Esperar un poco antes de reintentar
                                continue
                        else:
                            # Esperar un poco antes de reintentar si no podemos obtener la colección completa
                            time.sleep(1)
                            continue
                    
                    # Procesar cada item de la página actual
                    for item in items:
                        try:
                            # Obtener datos básicos
                            artist_name = "Unknown"
                            if hasattr(item.release, 'artists') and item.release.artists:
                                artist_name = item.release.artists[0].name
                                
                            label_name = ""
                            if hasattr(item.release, 'labels') and item.release.labels:
                                label_name = item.release.labels[0].name
                                
                            formats = ""
                            if hasattr(item.release, 'formats'):
                                formats = ', '.join(f.name for f in item.release.formats if hasattr(f, 'name'))
                                
                            # Crear diccionario con los datos
                            release_data = {
                                'release_id': item.release.id,
                                'Artist': artist_name,
                                'Title': item.release.title,
                                'Label': label_name,
                                'Format': formats,
                                'Released': getattr(item.release, 'year', ''),
                                'Genre': ', '.join(getattr(item.release, 'genres', [])),
                                'Style': ', '.join(getattr(item.release, 'styles', [])),
                                'Rating': getattr(item, 'rating', ''),
                                'Collection Media Condition': getattr(item, 'media_condition', ''),
                                'Collection Sleeve Condition': getattr(item, 'sleeve_condition', '')
                            }
                            releases.append(release_data)
                        except Exception as e:
                            logger.warning(f"Error procesando item: {e}")
                            continue
                        
                    # Esperar un momento para no exceder límites de API
                    time.sleep(1.5)
                    
                    # Ir a la siguiente página
                    page += 1
                    
                except Exception as e:
                    logger.warning(f"Error en la página {page}: {e}")
                    max_page_errors += 1
                    time.sleep(1)
            
            # Crear DataFrame
            if not releases:
                logger.error(f"No se encontraron discos en la colección de {username}")
                return None
                
            df = pd.DataFrame(releases)
            logger.info(f"Se obtuvieron {len(df)} discos de la colección de {username}")
            
            # Guardar a CSV para mantener compatibilidad con el flujo existente
            save_path = os.path.join(DATA_DIR, f"{username}_collection.csv")
            df.to_csv(save_path, index=False)
            logger.info(f"Colección guardada en {save_path}")
            
            return df, save_path
        except Exception as e:
            logger.error(f"Error obteniendo colección de {username}: {e}")
            return None

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
            logger.error("El cliente de Discogs no está inicializado")
            return collection_df
        
        if 'release_id' not in collection_df.columns:
            logger.error("El DataFrame no contiene la columna 'release_id'")
            return collection_df
        
        # Crear una copia para no modificar el original
        enriched_df = collection_df.copy()
        
        # Añadir columnas nuevas si no existen
        if 'original_release_year' not in enriched_df.columns:
            enriched_df['original_release_year'] = None
        if 'community_rating' not in enriched_df.columns:
            enriched_df['community_rating'] = None
        if 'image_url' not in enriched_df.columns:
            enriched_df['image_url'] = None
        if 'tracklist' not in enriched_df.columns:
            enriched_df['tracklist'] = None
        
        # Procesar cada release
        total_releases = len(enriched_df)
        logger.info(f"Enriqueciendo {total_releases} lanzamientos")
        
        for idx, row in enriched_df.iterrows():
            # Mostrar progreso cada 10 elementos
            if idx % 10 == 0:
                logger.info(f"Enriqueciendo elemento {idx+1} de {total_releases}")
            
            try:
                # Obtener el ID de lanzamiento, asegurando que sea un valor válido
                release_id = row['release_id']
                if pd.isna(release_id) or release_id == '':
                    logger.warning(f"ID de lanzamiento no válido en fila {idx}")
                    continue
                
                # Convertir a entero si es string numérico
                if isinstance(release_id, str) and release_id.isdigit():
                    release_id = int(release_id)
                
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
            except Exception as e:
                logger.warning(f"Error enriqueciendo lanzamiento en índice {idx}: {e}")
                continue
        
        logger.info(f"Proceso de enriquecimiento completado para {total_releases} lanzamientos")
        return enriched_df

    def get_user_collection_alternative(self, username):
        """
        Método alternativo para obtener la colección usando directamente las API REST de Discogs
        en lugar de la biblioteca cliente.
        
        Args:
            username: Nombre de usuario de Discogs
            
        Returns:
            tuple: (DataFrame con la colección, ruta del archivo guardado) o (None, None) si hay error
        """
        if not self.token:
            logger.error("Se requiere token para usar la API REST de Discogs")
            return None, None
        
        try:
            # URLs base para la API de Discogs
            base_url = "https://api.discogs.com"
            headers = {
                "Authorization": f"Discogs token={self.token}",
                "User-Agent": "VinylRecommender/1.0"
            }
            
            # Obtener los folders de la colección
            folders_url = f"{base_url}/users/{username}/collection/folders"
            logger.info(f"Obteniendo folders para {username}: {folders_url}")
            
            response = requests.get(folders_url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Error obteniendo folders: {response.status_code} - {response.text}")
                return None, None
            
            folders = response.json()
            if not folders or 'folders' not in folders:
                logger.error(f"No se encontraron folders para {username}")
                return None, None
            
            # Usar el folder 0 (All)
            folder_id = folders['folders'][0]['id']
            logger.info(f"Usando folder {folder_id} para {username}")
            
            # Obtener la colección paginada
            page = 1
            per_page = 100
            releases = []
            error_count = 0  # Contador de errores consecutivos
            
            while error_count < 2:  # Si tenemos 2 errores consecutivos, salimos del bucle
                releases_url = f"{base_url}/users/{username}/collection/folders/{folder_id}/releases?page={page}&per_page={per_page}"
                logger.info(f"Obteniendo página {page} para {username}: {releases_url}")
                
                response = requests.get(releases_url, headers=headers)
                
                # Verificar si la respuesta es exitosa
                if response.status_code == 200:
                    data = response.json()
                    
                    # Verificar si hay releases en esta página
                    if not data or 'releases' not in data or len(data['releases']) == 0:
                        logger.info(f"No hay más releases en la página {page}")
                        break
                    
                    # Reiniciar contador de errores ya que obtuvimos una página válida
                    error_count = 0
                    
                    # Procesar cada item
                    logger.info(f"Procesando {len(data['releases'])} releases de la página {page}")
                    for item in data['releases']:
                        try:
                            basic_info = item.get('basic_information', {})
                            
                            # Obtener datos básicos
                            artist_name = "Unknown"
                            if 'artists' in basic_info and basic_info['artists']:
                                artist_name = basic_info['artists'][0].get('name', "Unknown")
                                
                            label_name = ""
                            if 'labels' in basic_info and basic_info['labels']:
                                label_name = basic_info['labels'][0].get('name', "")
                                
                            formats = ""
                            if 'formats' in basic_info and basic_info['formats']:
                                format_names = [f.get('name', "") for f in basic_info['formats']]
                                formats = ', '.join(filter(None, format_names))
                                
                            # Crear diccionario con los datos
                            release_data = {
                                'release_id': basic_info.get('id', ""),
                                'Artist': artist_name,
                                'Title': basic_info.get('title', "Unknown"),
                                'Label': label_name,
                                'Format': formats,
                                'Released': basic_info.get('year', ""),
                                'Genre': ', '.join(basic_info.get('genres', [])),
                                'Style': ', '.join(basic_info.get('styles', [])),
                                'Rating': item.get('rating', ""),
                                'Collection Media Condition': item.get('notes', [{}])[0].get('value', "") if 'notes' in item and item['notes'] else "",
                                'Collection Sleeve Condition': item.get('notes', [{}])[-1].get('value', "") if 'notes' in item and len(item['notes']) > 1 else ""
                            }
                            releases.append(release_data)
                        except Exception as e:
                            logger.warning(f"Error procesando item: {e}")
                            continue
                    
                    # Verificar si hay más páginas
                    pagination = data.get('pagination', {})
                    total_pages = pagination.get('pages', 0)
                    
                    if page >= total_pages:
                        logger.info(f"Llegamos a la última página ({page} de {total_pages})")
                        break
                else:
                    # Error en la respuesta
                    error_count += 1
                    logger.error(f"Error obteniendo releases: {response.status_code} - {response.text}")
                    
                    # Si recibimos un 404 específicamente para el rango de páginas, salir
                    if response.status_code == 404 and "outside of valid range" in response.text:
                        logger.info("Llegamos al final de las páginas disponibles")
                        break
                    
                    # Esperar un poco más tiempo antes de reintentar en caso de error
                    time.sleep(2)
                    continue
                
                # Esperar para no exceder límites de API
                time.sleep(1.5)
                page += 1
            
            # Crear DataFrame
            if not releases:
                logger.error(f"No se encontraron discos en la colección de {username}")
                return None, None
                
            df = pd.DataFrame(releases)
            logger.info(f"Se obtuvieron {len(df)} discos de la colección de {username}")
            
            # Guardar a CSV para mantener compatibilidad con el flujo existente
            save_path = os.path.join(DATA_DIR, f"{username}_collection.csv")
            df.to_csv(save_path, index=False)
            logger.info(f"Colección guardada en {save_path}")
            
            return df, save_path
            
        except Exception as e:
            logger.error(f"Error obteniendo colección de {username} (método alternativo): {e}")
            return None, None


def save_enriched_collection(enriched_df, output_path=ENRICHED_COLLECTION_PATH):
    """
    Guarda la colección enriquecida en un nuevo archivo CSV
    
    Args:
        enriched_df: DataFrame con la colección enriquecida
        output_path: Ruta donde guardar el archivo
        
    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
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


def enrich_collection_from_file(input_csv_path=COLLECTION_CSV_PATH, output_csv_path=ENRICHED_COLLECTION_PATH, token=None):
    """
    Carga un archivo CSV de colección de Discogs y lo enriquece con datos adicionales
    
    Args:
        input_csv_path: Ruta al archivo CSV de la colección
        output_csv_path: Ruta para guardar el archivo enriquecido
        token: Token opcional para API de Discogs
        
    Returns:
        DataFrame: DataFrame con la colección enriquecida
    """
    try:
        # Cargar el CSV original
        df = pd.read_csv(input_csv_path)
        logger.info(f"CSV cargado correctamente: {len(df)} registros")
        
        # Inicializar conector de Discogs
        connector = DiscogsConnector(token=token)
        
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


def check_existing_collection(username):
    """
    Verifica si ya existe la colección de un usuario descargada localmente
    
    Args:
        username: Nombre de usuario de Discogs
        
    Returns:
        str: Ruta al archivo de colección existente, o None si no existe
    """
    # Verificar posibles rutas donde puede estar la colección
    expected_path = os.path.join(DATA_DIR, f"{username}_collection.csv")
    enriched_path = os.path.join(DATA_DIR, f"{username}_collection_enriched.csv")
    
    # Verificar si existe la versión enriquecida primero
    if os.path.exists(enriched_path):
        logger.info(f"Encontrada colección enriquecida existente para {username}: {enriched_path}")
        return enriched_path
    # Verificar si existe la versión normal
    elif os.path.exists(expected_path):
        logger.info(f"Encontrada colección existente para {username}: {expected_path}")
        return expected_path
    
    # No se encontró ninguna colección
    logger.info(f"No se encontró colección existente para {username}")
    return None


def get_user_collection_helper(username, token=None):
    """
    Función auxiliar para obtener la colección de un usuario de Discogs
    
    Args:
        username: Nombre de usuario de Discogs
        token: Token opcional para API de Discogs
        
    Returns:
        tuple: (DataFrame con la colección, ruta del archivo guardado)
    """
    try:
        logger.info(f"Obteniendo colección para el usuario: {username}")
        
        # Verificar si ya tenemos la colección descargada
        existing_path = check_existing_collection(username)
        if existing_path:
            logger.info(f"Usando colección existente para {username}: {existing_path}")
            try:
                df = pd.read_csv(existing_path)
                return df, existing_path
            except Exception as e:
                logger.error(f"Error leyendo colección existente: {e}. Intentando obtener de nuevo.")
                # Continuar con el proceso normal si hay error al leer la existente
        
        # Inicializar conector con el token proporcionado o el configurado
        connector = DiscogsConnector(token=token)
        
        if not connector.is_ready():
            logger.error("No se pudo inicializar el conector de Discogs")
            return None, None
            
        # Intentar obtener la colección con el método estándar primero
        result = connector.get_user_collection(username)
        
        # Si falló, intentar con el método alternativo
        if not result:
            logger.info("Método estándar falló, intentando método alternativo...")
            result = connector.get_user_collection_alternative(username)
        
        if not result:
            logger.error(f"No se pudo obtener la colección de {username} con ningún método")
            return None, None
            
        collection_df, save_path = result
            
        return collection_df, save_path
    except Exception as e:
        logger.error(f"Error obteniendo colección del usuario {username}: {e}")
        return None, None
