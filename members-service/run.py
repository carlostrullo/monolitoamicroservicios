from app.main import app

if __name__ == "__main__":
    # Decisión: puerto fijo por microservicio para el demo
    app.run(host="0.0.0.0", port=8001, debug=True)