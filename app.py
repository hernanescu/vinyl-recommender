import os
import logging
import pandas as pd
from flask import Flask, render_template, request, jsonify
import openai
from dotenv import load_dotenv

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

# Cargar variables de entorno (.env)
load_dotenv()

# Configurar OpenAI API
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("No se ha configurado OPENAI_API_KEY en el archivo .env")
else:
    logger.info("API Key de OpenAI configurada correctamente")
    
# Inicializar cliente de OpenAI (versión más reciente)
# Cambiando esta línea para evitar el error de 'proxies'
openai.api_key = api_key

app = Flask(__name__)

# Cargar datos de vinilos desde CSV
def load_vinyl_data(csv_path):
    try:
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
            'Collection Notes'
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
            year = v.get('Year', v.get('Released', ''))
            decade = v.get('Decade', '')
            genre = v.get('Genre_Clean', v.get('Genre', ''))
            style = v.get('Style_Clean', v.get('Style', ''))
            label = v.get('Label', '')
            format_type = v.get('Format_Type', v.get('Format', ''))
            condition = v.get('Media_Condition', '')
            
            # Construir entrada con información más rica
            entry = f"{i+1}. '{artist}' - '{title}'"
            
            # Agregar detalles relevantes
            details = []
            if year:
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
                
            vinyl_summary.append(entry)
        
        # Crear prompt para OpenAI con información enriquecida
        prompt = f"""
        Como experto en música, quiero que recomiendes álbumes de mi colección personal de vinilos.
        
        Mi colección incluye {len(vinyl_summary)} vinilos, aquí un detalle de cada uno:
        
        {vinyl_summary}
        
        Considerando:
        - Mi estado de ánimo actual es: {mood}
        - Mis intereses actuales son: {interests}
        
        Por favor, recomiéndame exactamente 3 álbumes de esta colección que sean adecuados para mi situación.
        
        En tu recomendación, ten en cuenta aspectos como:
        - El género y estilo musical y su relación con mi estado de ánimo
        - La época o década de lanzamiento si es relevante para mis intereses
        - Características especiales del álbum (instrumentación, temática, etc.)
        - La relación del artista o álbum con mis intereses expresados
        
        Formatea tu respuesta usando Markdown con el siguiente formato:
        
        ## Recomendaciones para tu momento {mood}
        
        ### 1. [Nombre del artista] - [Título del álbum] ([año])
        **Por qué es una buena elección:** Explicación detallada que mencione el género, estilo, 
        características del álbum y por qué encaja con mi estado de ánimo e intereses actuales...
        
        ### 2. [Nombre del artista] - [Título del álbum] ([año])
        **Por qué es una buena elección:** Explicación detallada...
        
        ### 3. [Nombre del artista] - [Título del álbum] ([año])
        **Por qué es una buena elección:** Explicación detallada...
        
        #### ¡Disfruta tu música!
        
        Asegúrate de que cada recomendación esté bien estructurada y justificada con información específica de la colección.
        """
        
        logger.debug(f"Prompt enviado a OpenAI: {prompt}")
        
        # Usar el cliente de OpenAI con la forma compatible
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un experto en música con amplio conocimiento de géneros, artistas, sellos discográficos y épocas musicales. Tus recomendaciones están bien fundamentadas y formateadas con markdown."},
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
            vinyl_data = load_vinyl_data('data/vinyl_collection.csv')
            
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
        
        vinyl_data = load_vinyl_data('data/vinyl_collection.csv')
        
        if vinyl_data is None:
            logger.error("API: No se pudo cargar la colección de vinilos")
            return jsonify({"error": "No se pudo cargar la colección de vinilos"}), 500
        
        recommendation = get_recommendation(vinyl_data, mood, interests)
        return jsonify({"recommendation": recommendation})
    except Exception as e:
        logger.error(f"Error en API: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Ruta para subir archivo CSV (opcional)
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
                    except Exception as e:
                        os.remove(file_path)  # Eliminar archivo inválido
                        error = f"El archivo no es un CSV válido: {str(e)}"
                        logger.error(f"CSV inválido: {e}")
        except Exception as e:
            error = f"Error al procesar el archivo: {str(e)}"
            logger.error(f"Error en subida de archivo: {e}", exc_info=True)
    
    return render_template('upload.html', error=error, success=success)

if __name__ == '__main__':
    logger.info("Iniciando aplicación")
    app.run(debug=True) 