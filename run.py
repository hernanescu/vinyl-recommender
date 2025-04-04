from app import create_app, logger

app = create_app()

if __name__ == '__main__':
    logger.info("Iniciando aplicación")
    app.run(debug=True)
