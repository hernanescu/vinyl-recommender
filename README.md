# Recomendador de Vinilos Personalizado

Una aplicación web para recomendar vinilos de tu colección personal basándose en tu estado de ánimo e intereses, utilizando la API de OpenAI.

## Características

- Importa tu colección de vinilos desde un archivo CSV de Discogs
- Obtén recomendaciones basadas en tu estado de ánimo actual
- Interfaz sencilla y amigable
- Enriquecimiento de tu colección con datos de Discogs (años originales, listas de canciones, valoraciones)
- Corrección inteligente de años de lanzamiento para álbumes clásicos

## Requisitos

- Python 3.7+
- Una clave API de OpenAI
- Un token de API de Discogs (opcional, para enriquecimiento)
- Un archivo CSV de tu colección de vinilos (exportado desde Discogs)

## Instalación

1. Clona este repositorio:
   ```
   git clone <url-del-repositorio>
   cd vinyl_project
   ```

2. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```

3. Configura tus claves API:
   - Copia el archivo `.env.example` a `.env` (o edita el existente)
   - Agrega tu clave API de OpenAI en el archivo `.env`
   - Agrega tu token de Discogs en el archivo `.env` (opcional)

## Uso

1. Ejecuta la aplicación:
   ```
   python run.py
   ```

2. Abre tu navegador y ve a `http://127.0.0.1:5000`

3. Sube tu archivo CSV de Discogs en la página de "Actualizar mi colección"

4. En la página principal, selecciona tu estado de ánimo y describe tus intereses

5. ¡Disfruta de las recomendaciones personalizadas de tu propia colección!

## Estructura del proyecto

```
/vinyl_project
  ├── app/                      # Carpeta principal de la aplicación
  │   ├── __init__.py           # Configuración de la aplicación
  │   ├── config.py             # Configuración global
  │   ├── models/               # Modelos de datos
  │   ├── services/             # Servicios externos (Discogs, OpenAI)
  │   │   ├── discogs_service.py # Interacción con Discogs
  │   │   └── openai_service.py  # Interacción con OpenAI
  │   ├── routes/               # Rutas de la aplicación
  │   │   ├── main_routes.py    # Rutas principales
  │   │   └── collection_routes.py # Rutas de gestión de colección
  │   └── utils/                # Utilidades
  │       └── vinyl_processor.py # Procesamiento de datos de vinilos
  ├── data/                     # Directorio para almacenar CSVs
  ├── static/                   # Archivos estáticos (CSS, JS)
  ├── templates/                # Plantillas HTML
  ├── .env                      # Variables de entorno
  ├── requirements.txt          # Dependencias
  └── run.py                    # Punto de entrada
```

## Cómo obtener tu colección de Discogs en CSV

1. Inicia sesión en tu cuenta de Discogs
2. Ve a tu colección
3. Haz clic en "Exportar"
4. Selecciona el formato CSV
5. Descarga el archivo
6. Súbelo en la página "Actualizar mi colección" de la aplicación

## Cómo obtener un token de API de Discogs

1. Inicia sesión en tu cuenta de Discogs
2. Ve a Configuración > Desarrolladores
3. Haz clic en "Generar nuevo token"
4. Copia el token y agrégalo a tu archivo `.env`

## Personalización

Puedes personalizar los estados de ánimo y otros aspectos de la aplicación editando las plantillas HTML en el directorio `/templates`.

También puedes agregar más correcciones para años de lanzamiento de álbumes específicos en el archivo `app/config.py`.

## Licencia

Este proyecto es de código abierto y está disponible para uso personal. 