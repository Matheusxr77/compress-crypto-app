"""
app.py - Ponto de entrada da aplicação Flask.

Responsabilidades:
  1. Criar a instância do Flask via application factory.
  2. Garantir (automaticamente) a existência das pastas dinâmicas de
     armazenamento usadas pelo pipeline de compressão/criptografia.
  3. Registrar os Blueprints das 4 abas da UI.

A lógica de negócio vive em core/ (extractors, crypto, compression,
pipeline, metrics) e é exposta ao usuário pelos Blueprints em routes/.
O processamento, a reversão, a inspeção dos artefatos e o dashboard de
métricas são expostos pelos Blueprints e usam os serviços de core/.
"""

import os

from flask import Flask

from config import Config


def create_app(config_class: type = Config) -> Flask:
    """Application factory: cria e configura a instância do Flask."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    _ensure_storage_folders(app)
    _register_blueprints(app)

    return app


def _ensure_storage_folders(app: Flask) -> None:
    """Cria automaticamente a árvore de pastas dinâmicas do pipeline.

    Cada etapa do processamento (upload -> criptografia -> compressão ->
    reversão -> métricas) tem seu próprio diretório isolado, o que facilita
    a inspeção manual (Aba 2) e a rastreabilidade de cada arquivo.
    """
    folders = [
        app.config["UPLOAD_FOLDER"],       # arquivos originais enviados
        app.config["ENCRYPTED_FOLDER"],    # arquivos após criptografia localizada
        app.config["COMPRESSED_FOLDER"],   # pacotes finais comprimidos
        app.config["RESTORED_FOLDER"],     # arquivos reconstruídos na reversão
        app.config["METRICS_FOLDER"],      # CSV/DB unificado de métricas
    ]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)


def _register_blueprints(app: Flask) -> None:
    """Registra os Blueprints das 4 abas principais."""
    from routes.dashboard_routes import dashboard_bp
    from routes.inspection_routes import inspection_bp
    from routes.reversal_routes import reversal_bp
    from routes.upload_routes import upload_bp

    app.register_blueprint(upload_bp)
    app.register_blueprint(inspection_bp)
    app.register_blueprint(reversal_bp)
    app.register_blueprint(dashboard_bp)


app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "").lower() == "true",
    )
