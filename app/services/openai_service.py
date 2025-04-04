import logging
import openai
from app.config import OPENAI_MODEL, OPENAI_API_KEY

logger = logging.getLogger(__name__)

def generate_recommendation(vinyl_summary, mood, interests, api_key=None):
    """
    Genera recomendaciones de vinilos usando OpenAI
    
    Args:
        vinyl_summary: Resumen de la colección de vinilos
        mood: Estado de ánimo del usuario
        interests: Intereses del usuario
        api_key: API key opcional de OpenAI (si no se proporciona, usa la clave configurada)
        
    Returns:
        str: Recomendación formateada en markdown
    """
    try:
        logger.info(f"Generando recomendación para mood: '{mood}', intereses: '{interests}'")
        
        # Configurar cliente con la API key proporcionada o la configurada
        previous_key = None
        if api_key:
            logger.info("Usando API key proporcionada por el usuario")
            # Guardar la API key anterior para restaurarla después
            previous_key = openai.api_key
            openai.api_key = api_key
        elif not openai.api_key:
            # Si no se ha configurado, usar la del archivo de configuración
            openai.api_key = OPENAI_API_KEY
        
        # Crear prompt para OpenAI con información enriquecida
        prompt = f"""
        Como experto en música, quiero que recomiendes álbumes de mi colección personal de vinilos.
        
        A continuación está mi colección de vinilos:

        {vinyl_summary}
        
        Considerando:
        - Mi estado de ánimo actual es: {mood}
        - Mis intereses actuales son: {interests}
        
        Por favor, recomiéndame exactamente 3 álbumes de esta colección que sean adecuados para mi situación.
        
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
        
        logger.debug(f"Prompt enviado a OpenAI (primeros 500 caracteres): {prompt[:500]}...")
        logger.debug(f"Longitud total del prompt: {len(prompt)} caracteres")
        
        # Usar el cliente de OpenAI
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Eres un experto en música con amplio conocimiento de géneros, artistas, sellos discográficos y épocas musicales. Tus recomendaciones están bien fundamentadas y formateadas con markdown. IMPORTANTE: Siempre usas el año ORIGINAL de lanzamiento de los discos, no el año de la edición particular."},
                {"role": "user", "content": prompt}
            ]
        )
        
        recommendation = response.choices[0].message.content
        logger.info("Recomendación generada exitosamente")
        
        # Restaurar la API key original si se cambió
        if api_key and previous_key:
            openai.api_key = previous_key
            
        return recommendation
    except Exception as e:
        # Restaurar la API key original en caso de error
        if api_key and previous_key:
            openai.api_key = previous_key
            
        logger.error(f"Error obteniendo recomendación: {e}", exc_info=True)
        return f"Error obteniendo recomendación: {str(e)}"
