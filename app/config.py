import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Directorios y rutas de archivos
DATA_DIR = 'data'
COLLECTION_CSV_PATH = os.path.join(DATA_DIR, 'vinyl_collection.csv')
ENRICHED_COLLECTION_PATH = os.path.join(DATA_DIR, 'enriched_collection.csv')

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCOGS_TOKEN = os.getenv("DISCOGS_TOKEN")

# Configuración de OpenAI
OPENAI_MODEL = "gpt-3.5-turbo"

# Configuración de sesión
SESSION_COLLECTION_KEY = 'current_collection_path'
SESSION_USERNAME_KEY = 'discogs_username'

# Diccionario de corrección para álbumes conocidos donde Discogs puede no tener el año correcto
KNOWN_ALBUM_YEARS = {
    'Led Zeppelin|Untitled': 1971,
    'Black Sabbath|Master Of Reality': 1971,
    'Pink Floyd|Meddle': 1971,
    'Pink Floyd|The Dark Side Of The Moon': 1973,
    'Pink Floyd|The Wall': 1979,
    'Pink Floyd|Wish You Were Here': 1975,
    'Pink Floyd|Animals': 1977
}
