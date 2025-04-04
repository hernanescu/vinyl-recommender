import logging
import pandas as pd
import os
from app.config import COLLECTION_CSV_PATH, ENRICHED_COLLECTION_PATH, KNOWN_ALBUM_YEARS

logger = logging.getLogger(__name__)

def load_vinyl_data(collection_path=None, use_enriched=True):
    """
    Carga datos de vinilos desde CSV (básico o enriquecido)
    
    Args:
        collection_path: Ruta opcional al archivo CSV (si no se proporciona, usa el predeterminado)
        use_enriched: Si es True, intenta usar la versión enriquecida si existe
        
    Returns:
        DataFrame: DataFrame con los datos de vinilos o None si hay error
    """
    try:
        # Determinar la ruta del archivo
        input_path = collection_path if collection_path else COLLECTION_CSV_PATH
        logger.info(f"Intentando cargar colección desde: {input_path}")
        
        # Verificar si el archivo existe
        if not os.path.exists(input_path):
            logger.error(f"El archivo especificado {input_path} no existe")
            
            # Si no existe y estamos usando collection_path personalizado, fallar
            if collection_path:
                logger.error(f"No se pudo cargar la colección personalizada: {collection_path}")
                return None
                
            # Si no existe y estamos usando el predeterminado, intentar otras opciones
            logger.warning(f"Intentando alternativas al no encontrar {COLLECTION_CSV_PATH}")
            if os.path.exists(ENRICHED_COLLECTION_PATH):
                logger.info(f"Cargando colección enriquecida predeterminada como alternativa")
                input_path = ENRICHED_COLLECTION_PATH
            else:
                # Buscar cualquier CSV que pueda servir en la carpeta data
                csv_files = [f for f in os.listdir('data') if f.endswith('.csv')]
                if csv_files:
                    input_path = os.path.join('data', csv_files[0])
                    logger.info(f"Usando primer CSV disponible encontrado: {input_path}")
                else:
                    logger.error("No se encontró ningún archivo CSV en la carpeta data")
                    return None
        
        # Si la ruta ya es un archivo enriquecido, usarla directamente
        if input_path.endswith('_enriched.csv') or 'enriched' in input_path:
            logger.info(f"Usando directamente el archivo enriquecido: {input_path}")
            df = pd.read_csv(input_path)
            logger.info(f"Se cargaron {len(df)} registros de vinilos enriquecidos desde {input_path}")
            return df
            
        # Verificar si existe una versión enriquecida
        if use_enriched:
            # Intentar construir el nombre del archivo enriquecido
            enriched_path = input_path.replace('.csv', '_enriched.csv')
            if not enriched_path.endswith('_enriched.csv'):
                enriched_path = input_path.replace('.csv', '') + '_enriched.csv'
                
            # Comprobar si existe
            if os.path.exists(enriched_path):
                logger.info(f"Cargando colección enriquecida desde {enriched_path}")
                df = pd.read_csv(enriched_path)
                logger.info(f"Se cargaron {len(df)} registros de vinilos enriquecidos")
                return df
        
        # Si llegamos aquí, cargamos el archivo original
        logger.info(f"Cargando datos desde el archivo original: {input_path}")
        df = pd.read_csv(input_path)
        logger.info(f"Se cargaron {len(df)} registros de vinilos desde {input_path}")
        return df
    except Exception as e:
        logger.error(f"Error cargando CSV: {e}", exc_info=True)
        return None

def process_vinyl_data(vinyl_data):
    """
    Procesa los datos de vinilos para obtener información relevante
    
    Args:
        vinyl_data: DataFrame de pandas con los datos de vinilos
        
    Returns:
        list: Lista de diccionarios con los datos procesados
    """
    try:
        # Verificar las columnas disponibles en el CSV
        available_columns = vinyl_data.columns.tolist()
        logger.info(f"Columnas disponibles en el CSV: {available_columns}")
        
        # Definir columnas relevantes para el análisis musical
        relevant_columns = [
            'Artist', 'Title', 'Label', 'Genre', 'Style', 
            'Released', 'Format', 'Rating', 'CollectionFolder',
            'Collection Media Condition', 'Collection Sleeve Condition',
            'Collection Notes', 'original_release_year', 'community_rating',
            'tracklist', 'image_url', 'release_id'
        ]
        
        # Filtrar para usar solo las columnas disponibles
        use_columns = [col for col in relevant_columns if col in available_columns]
        logger.info(f"Usando columnas: {use_columns}")
        
        # Crear una copia con las columnas disponibles
        if use_columns:
            processed_data = vinyl_data[use_columns].copy()
        else:
            processed_data = vinyl_data.copy()
            logger.warning("No se encontraron columnas esperadas. Usando todas las disponibles.")
        
        # Procesar los formatos para categorizarlos mejor
        if 'Format' in processed_data.columns:
            processed_data['Format_Clean'] = processed_data['Format'].apply(
                lambda x: str(x).replace('"', '').strip() if pd.notna(x) else "Desconocido"
            )
            # Extraer si es LP, Single, etc.
            processed_data['Format_Type'] = processed_data['Format_Clean'].apply(
                lambda x: 'LP' if 'LP' in x else 
                          'Single' if 'Single' in x else
                          '12"' if '12"' in x else
                          '7"' if '7"' in x else
                          'Otro'
            )
        
        # Procesar año de lanzamiento para mejorar recomendaciones por década
        if 'Released' in processed_data.columns:
            # Convertir a string y extraer el año (los primeros 4 dígitos)
            processed_data['Year'] = processed_data['Released'].astype(str).str.extract(r'(\d{4})', expand=False)
            # Obtener la década
            processed_data['Decade'] = processed_data['Year'].apply(
                lambda x: f"{x[0:3]}0s" if pd.notna(x) and len(str(x)) == 4 else "Desconocida"
            )
        
        # Usar el año original de lanzamiento si está disponible
        if 'original_release_year' in processed_data.columns:
            # Reemplazar el año con el año original si está disponible
            processed_data['Original_Year'] = processed_data['original_release_year']
            # Obtener la década original
            processed_data['Original_Decade'] = processed_data['Original_Year'].apply(
                lambda x: f"{str(x)[0:3]}0s" if pd.notna(x) and len(str(x)) == 4 else "Desconocida"
            )
        
        # Procesar géneros para mejor categorización
        if 'Genre' in processed_data.columns:
            processed_data['Genre_Clean'] = processed_data['Genre'].apply(
                lambda x: str(x).replace('"', '').strip() if pd.notna(x) else "Desconocido"
            )
        
        # Procesar estilos para mejor categorización
        if 'Style' in processed_data.columns:
            processed_data['Style_Clean'] = processed_data['Style'].apply(
                lambda x: str(x).replace('"', '').strip() if pd.notna(x) else "Desconocido"
            )
        
        # Procesar condición del vinilo
        if 'Collection Media Condition' in processed_data.columns:
            processed_data['Media_Condition'] = processed_data['Collection Media Condition'].apply(
                lambda x: str(x).strip() if pd.notna(x) else "Desconocida"
            )
        
        # Convertir a registros para el prompt
        vinyl_list = processed_data.to_dict('records')
        logger.info(f"Datos de vinilos procesados. Total: {len(vinyl_list)} registros")
        
        return vinyl_list
    except Exception as e:
        logger.error(f"Error procesando datos de vinilos: {e}", exc_info=True)
        return []

def prepare_vinyl_summary(vinyl_list, max_items=150):
    """
    Prepara un resumen detallado de la colección de vinilos para el prompt de OpenAI,
    limitando la cantidad de información para evitar exceder el límite de tokens.
    
    Args:
        vinyl_list: Lista de diccionarios con los datos de vinilos procesados
        max_items: Número máximo de vinilos a incluir en el resumen
        
    Returns:
        str: Texto con los resúmenes para cada vinilo
    """
    # Si hay más vinilos que el límite, seleccionar una muestra
    if len(vinyl_list) > max_items:
        logger.warning(f"La colección tiene {len(vinyl_list)} vinilos. Limitando a {max_items} para el prompt.")
        
        # Dar prioridad a discos con calificación (si está disponible)
        if any('Rating' in v and v['Rating'] and pd.notna(v['Rating']) for v in vinyl_list):
            # Ordenar por calificación (descendente) y tomar los mejores
            rated_vinyls = [v for v in vinyl_list if 'Rating' in v and v['Rating'] and pd.notna(v['Rating'])]
            rated_vinyls.sort(key=lambda x: float(x['Rating']) if isinstance(x['Rating'], (int, float, str)) and str(x['Rating']).replace('.', '', 1).isdigit() else 0, reverse=True)
            
            # Tomar el 70% de los mejores calificados
            top_rated = rated_vinyls[:int(max_items * 0.7)]
            
            # El resto tomarlos aleatoriamente de los no calificados o de menor calificación
            remaining = max_items - len(top_rated)
            if remaining > 0:
                other_vinyls = [v for v in vinyl_list if v not in top_rated]
                import random
                random_selection = random.sample(other_vinyls, min(remaining, len(other_vinyls)))
                selected_vinyls = top_rated + random_selection
            else:
                selected_vinyls = top_rated[:max_items]
        else:
            # Si no hay calificaciones, tomar muestra aleatoria
            import random
            selected_vinyls = random.sample(vinyl_list, max_items)
    else:
        selected_vinyls = vinyl_list
    
    # Generar resúmenes simplificados con información esencial
    vinyl_summaries = []
    
    for i, v in enumerate(selected_vinyls):
        # Información esencial: Artista, Título, Año, Género
        artist = v.get('Artist', 'Unknown Artist')
        title = v.get('Title', 'Unknown Title')
        
        # Buscar en el diccionario de corrección para este álbum
        album_key = f"{artist}|{title}"
        corrected_year = KNOWN_ALBUM_YEARS.get(album_key)
        
        # Extraer información de año, priorizando el año original
        year = v.get('Original_Year', v.get('original_release_year', v.get('Year', v.get('Released', ''))))
        
        # Usar el año corregido si está disponible en nuestro diccionario
        if corrected_year:
            year = corrected_year
        
        # Información de género y estilo, simplificada
        genre = v.get('Genre_Clean', v.get('Genre', ''))
        style = v.get('Style_Clean', v.get('Style', ''))
        
        # Construir resumen simplificado
        summary = f"{artist} - {title} ({year})"
        
        # Añadir información de género/estilo solo si está disponible
        if genre or style:
            genre_info = []
            if genre:
                genre_info.append(genre)
            if style and style != genre:
                genre_info.append(style)
            
            if genre_info:
                summary += f" | {', '.join(genre_info)}"
        
        vinyl_summaries.append(summary)
    
    # Unir todos los resúmenes en un solo texto
    result = "\n".join(vinyl_summaries)
    
    # Información sobre la muestra
    if len(vinyl_list) > max_items:
        note = f"NOTA: Tu colección completa tiene {len(vinyl_list)} discos. Este resumen incluye una muestra de {len(selected_vinyls)} discos representativos."
        result = note + "\n\n" + result
    
    return result
