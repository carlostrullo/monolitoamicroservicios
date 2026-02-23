from flask import Flask, jsonify
from app.infraestructure.db import init_db
from app.api.trainers import bp as trainers_bp

def create_app() -> Flask:
    app = Flask(__name__)
    init_db()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    app.register_blueprint(trainers_bp)
    return app

app = create_app()