from flask import Flask, jsonify
from app.infraestructure.db import init_db
from app.api.classes import bp as classes_bp
from app.swagger import init_swagger

def create_app() -> Flask:
    app = Flask(__name__)

    app.config["API_TITLE"] = "Classes Service API"
    app.config["API_VERSION"] = "v1"
    app.config["API_DESCRIPTION"] = "Documentación Swagger del servicio de clases"

    init_db()
    init_swagger(app)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    app.register_blueprint(classes_bp)
    return app

app = create_app()