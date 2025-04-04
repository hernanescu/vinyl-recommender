# Recomendador de Vinilos Personalizado

Una aplicación web simple para recomendar vinilos de tu colección personal basándose en tu estado de ánimo e intereses, utilizando la API de OpenAI.

## Características

- Importa tu colección de vinilos desde un archivo CSV de Discogs
- Obtén recomendaciones basadas en tu estado de ánimo actual
- Interfaz sencilla y amigable
- Personalizable para diferentes preferencias

## Requisitos

- Python 3.7+
- Una clave API de OpenAI
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

3. Configura tu clave API de OpenAI:
   - Copia el archivo `.env.example` a `.env` (o edita el existente)
   - Agrega tu clave API de OpenAI en el archivo `.env`

## Uso

1. Ejecuta la aplicación:
   ```
   flask run
   ```

2. Abre tu navegador y ve a `http://127.0.0.1:5000`

3. Sube tu archivo CSV de Discogs en la página de "Actualizar mi colección"

4. En la página principal, selecciona tu estado de ánimo y describe tus intereses

5. ¡Disfruta de las recomendaciones personalizadas de tu propia colección!

## Estructura del proyecto

```
/vinyl_project
  ├── app.py           # Aplicación principal Flask
  ├── /data            # Directorio para almacenar la colección de vinilos en CSV
  ├── /static          # Archivos estáticos (CSS, JS)
  ├── /templates       # Plantillas HTML
  ├── .env             # Variables de entorno
  └── requirements.txt # Dependencias
```

## Cómo obtener tu colección de Discogs en CSV

1. Inicia sesión en tu cuenta de Discogs
2. Ve a tu colección
3. Haz clic en "Exportar"
4. Selecciona el formato CSV
5. Descarga el archivo
6. Súbelo en la página "Actualizar mi colección" de la aplicación

## Personalización

Puedes personalizar los estados de ánimo y otros aspectos de la aplicación editando las plantillas HTML en el directorio `/templates`.

## Licencia

Este proyecto es de código abierto y está disponible para uso personal. 