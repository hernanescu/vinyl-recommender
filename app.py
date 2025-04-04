import os
import logging
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for
import openai
from dotenv import load_dotenv
import discogs_api

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Configurar OpenAI API
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("No se ha configurado OPENAI_API_KEY en el archivo .env")
else:
    logger.info("API Key de OpenAI configurada correctamente")
    
# Inicializar cliente de OpenAI con la forma compatible
openai.api_key = api_key

# Inicializar la aplicación Flask
app = Flask(__name__)

# Rutas de archivos
COLLECTION_CSV_PATH = 'data/vinyl_collection.csv'
ENRICHED_COLLECTION_PATH = 'data/enriched_collection.csv'

# Cargar datos de vinilos desde CSV (básico o enriquecido)
def load_vinyl_data(csv_path, use_enriched=True):
    try:
        # Verificar si existe una versión enriquecida primero
        if use_enriched and os.path.exists(ENRICHED_COLLECTION_PATH):
            logger.info(f"Cargando colección enriquecida desde {ENRICHED_COLLECTION_PATH}")
            df = pd.read_csv(ENRICHED_COLLECTION_PATH)
            logger.info(f"Se cargaron {len(df)} registros de vinilos enriquecidos")
            return df
            
        # Si no hay enriquecida o no se quiere usar, cargar la normal
        if not os.path.exists(csv_path):
            logger.error(f"El archivo {csv_path} no existe")
            return None
            
        logger.info(f"Cargando datos desde {csv_path}")
        df = pd.read_csv(csv_path)
        logger.info(f"Se cargaron {len(df)} registros de vinilos")
        return df
    except Exception as e:
        logger.error(f"Error cargando CSV: {e}", exc_info=True)
        return None

# Procesar los datos de vinilos para obtener información relevante
def process_vinyl_data(vinyl_data):
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

# Función para obtener recomendación de OpenAI
def get_recommendation(vinyl_data, mood, interests):
    try:
        logger.info(f"Generando recomendación para mood: '{mood}', intereses: '{interests}'")
        
        # Procesar datos para el prompt
        vinyl_list = process_vinyl_data(vinyl_data)
        
        # Crear un resumen más detallado y útil para OpenAI
        vinyl_summary = []
        for i, v in enumerate(vinyl_list):
            artist = v.get('Artist', 'Unknown Artist')
            title = v.get('Title', 'Unknown Title')
            
            # Extraer información adicional cuando esté disponible
            year = v.get('Original_Year', v.get('Year', v.get('Released', '')))
            original_year = v.get('original_release_year', None)
            decade = v.get('Original_Decade', v.get('Decade', ''))
            genre = v.get('Genre_Clean', v.get('Genre', ''))
            style = v.get('Style_Clean', v.get('Style', ''))
            label = v.get('Label', '')
            format_type = v.get('Format_Type', v.get('Format', ''))
            condition = v.get('Media_Condition', '')
            community_rating = v.get('community_rating', '')
            
            # Incluir tracklist si está disponible (solo para los primeros 20 vinilos para no sobrecargar el prompt)
            tracklist = v.get('tracklist', '') if i < 20 else ''
            
            # Construir entrada con información más rica
            entry = f"{i+1}. '{artist}' - '{title}'"
            
            # Agregar detalles relevantes
            details = []
            if original_year:
                details.append(f"año original: {original_year}")
            elif year:
                details.append(f"año: {year}")
            if genre:
                details.append(f"género: {genre}")
            if style:
                details.append(f"estilo: {style}")
            if label:
                details.append(f"sello: {label}")
            if format_type:
                details.append(f"formato: {format_type}")
            
            # Agregar detalles a la entrada
            if details:
                entry += f" ({', '.join(details)})"
                
            # Agregar tracklist si está disponible
            if tracklist:
                entry += f"\n     Canciones: {tracklist}"
                
            vinyl_summary.append(entry)
        
        # Crear prompt para OpenAI con información enriquecida
        prompt = f"""
        Sos un experto en música, simpático e influyente. Dominás conocimiento sobre música, cultura, psicología y entendimiento general.
        Quiero que me recomiendes discos de mi colección personal de vinilos.
        
        Mi colección incluye {len(vinyl_summary)} vinilos, y te envío acá un detalle de cada uno:
        
        {vinyl_summary}
        
        Considerando:
        - Mi estado de ánimo actual es: {mood}
        - Mis intereses actuales son: {interests}
        
        Por favor, recomendame exactamente 3 álbumes de esta colección que sean adecuados para mi situación. Hacé un mensaje de 100 palabras máximo, y ponele onda.
        
        IMPORTANTE: Es OBLIGATORIO usar el año ORIGINAL de lanzamiento del álbum, nunca uses el año de la edición.
        Por ejemplo, si Led Zeppelin IV se lanzó originalmente en 1971 pero mi copia es de 2022, siempre debes presentar el álbum como de 1971.
        
        En tu recomendación, ten en cuenta aspectos como:
        - El género y estilo musical y su relación con mi estado de ánimo
        - La época o década de lanzamiento si es relevante para mis intereses
        - Características especiales del álbum (instrumentación, temática, canciones específicas, etc.)
        - La relación del artista o álbum con mis intereses expresados
        
        NO menciones puntajes ni valoraciones numéricas en tus recomendaciones.
        
        Formatea tu respuesta usando Markdown con el siguiente formato:
        
        ## Recomendaciones para tu momento {mood}
        
        ### 1. [Nombre del artista] - [Título del álbum] ([año ORIGINAL])
        **Por qué es una buena elección:** Explicación detallada que mencione el género, estilo, 
        características del álbum y por qué encaja con mi estado de ánimo e intereses actuales...
        
        ### 2. [Nombre del artista] - [Título del álbum] ([año ORIGINAL])
        **Por qué es una buena elección:** Explicación detallada...
        
        ### 3. [Nombre del artista] - [Título del álbum] ([año ORIGINAL])
        **Por qué es una buena elección:** Explicación detallada...
        
        #### ¡Disfruta tu música!
        
        Asegúrate de que cada recomendación esté bien estructurada y justificada con información específica de la colección.
        """
        
        logger.debug(f"Prompt enviado a OpenAI: {prompt}")
        
        # Usar el cliente de OpenAI con la forma compatible
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un experto en música con amplio conocimiento de géneros, artistas, sellos discográficos y épocas musicales. Tus recomendaciones están bien fundamentadas y formateadas con markdown. IMPORTANTE: Siempre usas el año ORIGINAL de lanzamiento de los discos, no el año de la edición particular."},
                {"role": "user", "content": prompt}
            ]
        )
        
        recommendation = response.choices[0].message.content
        logger.info("Recomendación generada exitosamente")
        return recommendation
    except Exception as e:
        logger.error(f"Error obteniendo recomendación: {e}", exc_info=True)
        return f"Error obteniendo recomendación: {str(e)}"

# Ruta principal
@app.route('/', methods=['GET', 'POST'])
def index():
    recommendation = None
    error = None
    
    if request.method == 'POST':
        try:
            # Obtener parámetros del formulario
            mood = request.form.get('mood', '')
            interests = request.form.get('interests', '')
            
            logger.info(f"Solicitud de recomendación recibida. Mood: {mood}, Intereses: {interests}")
            
            # Cargar datos de vinilos
            vinyl_data = load_vinyl_data(COLLECTION_CSV_PATH)
            
            if vinyl_data is not None:
                # Obtener recomendación
                recommendation = get_recommendation(vinyl_data, mood, interests)
            else:
                error = "No se pudo cargar la colección de vinilos. Por favor, sube un archivo CSV válido."
                logger.error(error)
        except Exception as e:
            error = f"Error inesperado: {str(e)}"
            logger.error(f"Error en ruta principal: {e}", exc_info=True)
    
    return render_template('index.html', recommendation=recommendation, error=error)

# API para obtener recomendación (opcional, para uso futuro)
@app.route('/api/recommend', methods=['POST'])
def api_recommend():
    try:
        data = request.json
        mood = data.get('mood', '')
        interests = data.get('interests', '')
        
        logger.info(f"API: Solicitud de recomendación. Mood: {mood}, Intereses: {interests}")
        
        vinyl_data = load_vinyl_data(COLLECTION_CSV_PATH)
        
        if vinyl_data is None:
            logger.error("API: No se pudo cargar la colección de vinilos")
            return jsonify({"error": "No se pudo cargar la colección de vinilos"}), 500
        
        recommendation = get_recommendation(vinyl_data, mood, interests)
        return jsonify({"recommendation": recommendation})
    except Exception as e:
        logger.error(f"Error en API: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Ruta para subir archivo CSV
@app.route('/upload', methods=['GET', 'POST'])
def upload_csv():
    error = None
    success = None
    
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                error = "No se seleccionó archivo"
                logger.warning("Intento de subida sin archivo seleccionado")
            else:
                file = request.files['file']
                if file.filename == '':
                    error = "No se seleccionó archivo"
                    logger.warning("Nombre de archivo vacío en la subida")
                elif not file.filename.endswith('.csv'):
                    error = "El archivo debe ser un CSV"
                    logger.warning(f"Intento de subir archivo no CSV: {file.filename}")
                else:
                    # Asegurar que el directorio 'data' existe
                    os.makedirs('data', exist_ok=True)
                    
                    # Guardar el archivo
                    file_path = os.path.join('data', 'vinyl_collection.csv')
                    file.save(file_path)
                    
                    # Validar que el archivo es un CSV válido
                    try:
                        df = pd.read_csv(file_path)
                        logger.info(f"Archivo CSV subido y validado: {len(df)} registros")
                        success = f"Archivo subido correctamente. Se cargaron {len(df)} registros."
                        
                        # Verificar si se quiere enriquecer los datos
                        enrich = request.form.get('enrich') == 'yes'
                        if enrich:
                            logger.info("Iniciando proceso de enriquecimiento con Discogs API")
                            success += " Enriquecimiento en proceso..."
                            return redirect(url_for('enrich_data'))
                    except Exception as e:
                        os.remove(file_path)  # Eliminar archivo inválido
                        error = f"El archivo no es un CSV válido: {str(e)}"
                        logger.error(f"CSV inválido: {e}")
        except Exception as e:
            error = f"Error al procesar el archivo: {str(e)}"
            logger.error(f"Error en subida de archivo: {e}", exc_info=True)
    
    return render_template('upload.html', error=error, success=success)

# Ruta para enriquecer datos con Discogs API
@app.route('/enrich', methods=['GET'])
def enrich_data():
    error = None
    success = None
    
    try:
        if not os.path.exists(COLLECTION_CSV_PATH):
            error = "No se encontró el archivo CSV de la colección. Por favor, sube un archivo primero."
            logger.error(error)
        else:
            # Iniciar el proceso de enriquecimiento
            logger.info("Iniciando proceso de enriquecimiento desde la interfaz web")
            
            # Enriquecer los datos (en background para no bloquear la interfaz sería lo ideal)
            # Pero para simplicidad, lo hacemos sincrónicamente
            enriched_df = discogs_api.enrich_collection_from_file(
                COLLECTION_CSV_PATH, 
                ENRICHED_COLLECTION_PATH
            )
            
            if enriched_df is not None and len(enriched_df) > 0:
                success = f"¡Enriquecimiento completado! Se enriquecieron {len(enriched_df)} registros."
                logger.info(f"Enriquecimiento completado para {len(enriched_df)} registros")
            else:
                error = "No se pudo enriquecer la colección. Verifica el log para más detalles."
                logger.error("Fallo en el proceso de enriquecimiento")
    except Exception as e:
        error = f"Error durante el enriquecimiento: {str(e)}"
        logger.error(f"Error en proceso de enriquecimiento: {e}", exc_info=True)
    
    return render_template('enrich.html', error=error, success=success)

if __name__ == '__main__':
    logger.info("Iniciando aplicación")
    app.run(debug=True) 