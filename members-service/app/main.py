from flask import Flask, jsonify

from app.infraestructure.db import init_db
from app.api.members import bp as members_bp


def create_app() -> Flask:
    app = Flask(__name__)

    # Decisión: inicializar DB al arrancar el servicio (simple y suficiente para el taller)
    init_db()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    # Decisión: usamos Blueprint para separar rutas y mantener orden (API como “capa”)
    app.register_blueprint(members_bp)

    return app


app = create_app()