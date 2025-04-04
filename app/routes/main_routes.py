import logging
import markdown
from flask import Blueprint, render_template, request, jsonify, session
from app.utils.vinyl_processor import load_vinyl_data, process_vinyl_data, prepare_vinyl_summary
from app.services.openai_service import generate_recommendation
from app.config import SESSION_COLLECTION_KEY, COLLECTION_CSV_PATH

logger = logging.getLogger(__name__)

# Crear Blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET', 'POST'])
def index():
    """
    Ruta principal que muestra el formulario y genera recomendaciones
    """
    recommendation = None
    error = None
    
    # Obtener información de la colección
    collection_path = session.get(SESSION_COLLECTION_KEY, COLLECTION_CSV_PATH)
    username = session.get('discogs_username', None)
    
    logger.info(f"Cargando página principal. Colección actual: {collection_path}, Usuario: {username}")
    
    if request.method == 'POST':
        try:
            # Obtener parámetros del formulario
            mood = request.form.get('mood', '')
            interests = request.form.get('interests', '')
            openai_key = request.form.get('openai_key', None)
            
            logger.info(f"Solicitud de recomendación recibida. Mood: '{mood}', Intereses: '{interests}', API key personalizada: {'Sí' if openai_key else 'No'}")
            logger.info(f"Usando colección en {collection_path} para usuario {username}")
            
            # Cargar datos de vinilos
            vinyl_data = load_vinyl_data(collection_path=collection_path)
            
            if vinyl_data is not None:
                logger.info(f"Colección cargada correctamente con {len(vinyl_data)} vinilos")
                
                # Procesar datos para obtener información enriquecida
                vinyl_list = process_vinyl_data(vinyl_data)
                
                # Preparar resumen para el prompt de OpenAI (limitado para evitar exceder límite de tokens)
                # Limitar a 150 vinilos máximo para colecciones grandes
                vinyl_summary = prepare_vinyl_summary(vinyl_list, max_items=150)
                
                # Verificar longitud aproximada en tokens
                approx_tokens = len(vinyl_summary) / 4  # Estimación aproximada
                logger.info(f"Longitud aproximada del resumen: ~{approx_tokens:.0f} tokens")
                
                # Obtener recomendación con la API key proporcionada (si existe)
                markdown_text = generate_recommendation(vinyl_summary, mood, interests, api_key=openai_key)
                
                # Convertir el markdown a HTML
                recommendation = markdown.markdown(markdown_text)
            else:
                error = "No se pudo cargar la colección de vinilos. Por favor, sube un archivo CSV válido o proporciona un usuario de Discogs."
                logger.error(error)
        except Exception as e:
            error = f"Error inesperado: {str(e)}"
            logger.error(f"Error en ruta principal: {e}", exc_info=True)
    
    # Preparar contexto para la plantilla
    context = {
        'recommendation': recommendation,
        'error': error,
        'collection_loaded': session.get(SESSION_COLLECTION_KEY) is not None,
        'username': username,
        'collection_path': collection_path
    }
    
    return render_template('index.html', **context)

@main_bp.route('/api/recommend', methods=['POST'])
def api_recommend():
    """
    API para obtener recomendación (para uso futuro o integración con otras apps)
    """
    try:
        data = request.json
        mood = data.get('mood', '')
        interests = data.get('interests', '')
        openai_key = data.get('openai_key', None)
        collection_path = data.get('collection_path', session.get(SESSION_COLLECTION_KEY, COLLECTION_CSV_PATH))
        
        logger.info(f"API: Solicitud de recomendación. Mood: '{mood}', Intereses: '{interests}', API key personalizada: {'Sí' if openai_key else 'No'}")
        
        vinyl_data = load_vinyl_data(collection_path=collection_path)
        
        if vinyl_data is None:
            logger.error("API: No se pudo cargar la colección de vinilos")
            return jsonify({"error": "No se pudo cargar la colección de vinilos"}), 500
        
        # Procesar datos para obtener información enriquecida
        vinyl_list = process_vinyl_data(vinyl_data)
        
        # Preparar resumen para el prompt de OpenAI
        vinyl_summary = prepare_vinyl_summary(vinyl_list)
        
        # Obtener recomendación con la API key proporcionada (si existe)
        markdown_text = generate_recommendation(vinyl_summary, mood, interests, api_key=openai_key)
        
        # Convertir el markdown a HTML para clientes que lo necesiten
        html_recommendation = markdown.markdown(markdown_text)
        
        return jsonify({
            "recommendation": markdown_text,
            "recommendation_html": html_recommendation
        })
    except Exception as e:
        logger.error(f"Error en API: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
