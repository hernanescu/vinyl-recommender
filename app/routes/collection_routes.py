import logging
import os
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.config import COLLECTION_CSV_PATH, ENRICHED_COLLECTION_PATH, DATA_DIR, SESSION_COLLECTION_KEY, SESSION_USERNAME_KEY
from app.services.discogs_service import enrich_collection_from_file, get_user_collection_helper

logger = logging.getLogger(__name__)

# Crear Blueprint
collection_bp = Blueprint('collection', __name__)

@collection_bp.route('/upload', methods=['GET', 'POST'])
def upload_csv():
    """
    Ruta para subir archivo CSV de la colección
    """
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
                    os.makedirs(os.path.dirname(COLLECTION_CSV_PATH), exist_ok=True)
                    
                    # Guardar el archivo
                    file.save(COLLECTION_CSV_PATH)
                    
                    # Guardar la ruta en la sesión
                    session[SESSION_COLLECTION_KEY] = COLLECTION_CSV_PATH
                    
                    # Validar que el archivo es un CSV válido
                    try:
                        df = pd.read_csv(COLLECTION_CSV_PATH)
                        logger.info(f"Archivo CSV subido y validado: {len(df)} registros")
                        success = f"Archivo subido correctamente. Se cargaron {len(df)} registros."
                        
                        # Verificar si se quiere enriquecer los datos
                        enrich = request.form.get('enrich') == 'yes'
                        if enrich:
                            logger.info("Iniciando proceso de enriquecimiento con Discogs API")
                            flash("Colección cargada. Iniciando enriquecimiento de datos...", 'success')
                            return redirect(url_for('collection.enrich_data'))
                        else:
                            # Redirigir al índice con mensaje de éxito
                            flash(success, 'success')
                            return redirect(url_for('main.index'))
                    except Exception as e:
                        os.remove(COLLECTION_CSV_PATH)  # Eliminar archivo inválido
                        error = f"El archivo no es un CSV válido: {str(e)}"
                        logger.error(f"CSV inválido: {e}")
        except Exception as e:
            error = f"Error al procesar el archivo: {str(e)}"
            logger.error(f"Error en subida de archivo: {e}", exc_info=True)
    
    return render_template('upload.html', error=error, success=success)

@collection_bp.route('/user', methods=['GET', 'POST'])
def get_user_collection():
    """
    Obtiene la colección de un usuario de Discogs
    """
    error = None
    success = None
    
    if request.method == 'POST':
        try:
            # Limpiar datos de sesión anteriores
            if SESSION_COLLECTION_KEY in session:
                logger.info(f"Eliminando referencia a colección anterior: {session[SESSION_COLLECTION_KEY]}")
            
            username = request.form.get('username', '').strip()
            token = request.form.get('token', None)
            
            if not username:
                error = "Debes proporcionar un nombre de usuario de Discogs"
                logger.warning("Intento de obtener colección sin nombre de usuario")
            else:
                logger.info(f"Obteniendo colección para el usuario: {username}")
                
                # Obtener colección
                collection_df, save_path = get_user_collection_helper(username, token)
                
                if collection_df is not None and save_path is not None:
                    # Guardar información en la sesión
                    session[SESSION_COLLECTION_KEY] = save_path
                    session[SESSION_USERNAME_KEY] = username
                    
                    logger.info(f"Actualizado SESSION_COLLECTION_KEY={save_path}, SESSION_USERNAME_KEY={username}")
                    
                    success = f"¡Colección obtenida! Se encontraron {len(collection_df)} discos en la colección de {username}."
                    logger.info(f"Colección obtenida para {username}: {len(collection_df)} discos")
                    
                    # Redirigir al índice con mensaje de éxito
                    flash(success, 'success')
                    return redirect(url_for('main.index'))
                else:
                    error = f"No se pudo obtener la colección del usuario {username}. Verifica que el usuario exista y su colección sea pública."
                    logger.error(f"Error obteniendo colección para {username}")
        except Exception as e:
            error = f"Error al obtener la colección: {str(e)}"
            logger.error(f"Error obteniendo colección de usuario: {e}", exc_info=True)
    
    return render_template('user_collection.html', error=error, success=success)

@collection_bp.route('/enrich', methods=['GET', 'POST'])
def enrich_data():
    """
    Ruta para enriquecer datos con Discogs API
    """
    error = None
    success = None
    
    # Obtener la ruta del archivo CSV de la sesión o usar el predeterminado
    collection_path = session.get(SESSION_COLLECTION_KEY, COLLECTION_CSV_PATH)
    
    if request.method == 'POST':
        token = request.form.get('token', None)
        custom_output = request.form.get('custom_output', None)
        
        output_path = ENRICHED_COLLECTION_PATH
        if custom_output:
            output_path = os.path.join(DATA_DIR, custom_output)
            
        try:
            if not os.path.exists(collection_path):
                error = "No se encontró el archivo CSV de la colección. Por favor, sube un archivo primero o proporciona un usuario de Discogs."
                logger.error(error)
            else:
                # Iniciar el proceso de enriquecimiento
                logger.info(f"Iniciando proceso de enriquecimiento para {collection_path}")
                
                # Enriquecer los datos
                enriched_df = enrich_collection_from_file(
                    input_csv_path=collection_path, 
                    output_csv_path=output_path,
                    token=token
                )
                
                if enriched_df is not None and len(enriched_df) > 0:
                    success = f"¡Enriquecimiento completado! Se enriquecieron {len(enriched_df)} registros."
                    logger.info(f"Enriquecimiento completado para {len(enriched_df)} registros")
                    
                    # Actualizar el archivo de colección en la sesión
                    session[SESSION_COLLECTION_KEY] = output_path
                    
                    # Redirigir al índice con mensaje de éxito
                    flash(success, 'success')
                    return redirect(url_for('main.index'))
                else:
                    error = "No se pudo enriquecer la colección. Verifica el log para más detalles."
                    logger.error("Fallo en el proceso de enriquecimiento")
        except Exception as e:
            error = f"Error durante el enriquecimiento: {str(e)}"
            logger.error(f"Error en proceso de enriquecimiento: {e}", exc_info=True)
    
    return render_template('enrich.html', error=error, success=success)

@collection_bp.route('/clear-data', methods=['GET', 'POST'])
def clear_data():
    """
    Ruta para eliminar todos los archivos CSV de colecciones en la carpeta data
    """
    error = None
    success = None
    
    if request.method == 'POST':
        try:
            # Obtener todos los archivos CSV del directorio de datos
            import os
            import glob
            
            # Patrón para buscar archivos CSV en la carpeta data
            csv_files = glob.glob(os.path.join(DATA_DIR, '*.csv'))
            
            if not csv_files:
                logger.info("No se encontraron archivos CSV para eliminar")
                success = "No hay archivos de colección para eliminar."
            else:
                # Eliminar cada archivo CSV
                deleted_count = 0
                for file_path in csv_files:
                    try:
                        os.remove(file_path)
                        logger.info(f"Archivo eliminado: {file_path}")
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Error eliminando archivo {file_path}: {e}")
                
                # Limpiar variables de sesión relacionadas con colecciones
                if SESSION_COLLECTION_KEY in session:
                    del session[SESSION_COLLECTION_KEY]
                if SESSION_USERNAME_KEY in session:
                    del session[SESSION_USERNAME_KEY]
                
                logger.info(f"Se eliminaron {deleted_count} archivos CSV y se limpió la sesión")
                success = f"Se eliminaron {deleted_count} archivos de colección correctamente y se limpió la sesión."
                
                # Redirigir al índice con mensaje de éxito
                flash(success, 'success')
                return redirect(url_for('main.index'))
                
        except Exception as e:
            error = f"Error al limpiar datos: {str(e)}"
            logger.error(f"Error en limpieza de datos: {e}", exc_info=True)
    
    return render_template('clear_data.html', error=error, success=success)
