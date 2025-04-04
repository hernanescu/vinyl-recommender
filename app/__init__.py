import logging
import os
from flask import Flask
import openai
from app.config import OPENAI_API_KEY
import secrets

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

# Crear y configurar la aplicación
def create_app():
    # Inicializar la aplicación Flask
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '../templates'),
                static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '../static'))
    
    # Configurar clave secreta para sesiones
    app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))
    
    # Configurar OpenAI API
    if not OPENAI_API_KEY:
        logger.error("No se ha configurado OPENAI_API_KEY en el archivo .env")
    else:
        logger.info("API Key de OpenAI configurada correctamente")
        openai.api_key = OPENAI_API_KEY
    
    # Registrar rutas
    from app.routes.main_routes import main_bp
    from app.routes.collection_routes import collection_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(collection_bp, url_prefix='/collection')
    
    # Asegurar que el directorio de datos existe
    from app.config import DATA_DIR
    os.makedirs(DATA_DIR, exist_ok=True)
    
    return app
