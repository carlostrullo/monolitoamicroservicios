from flasgger import Swagger

def init_swagger(app):
    template = {
        "swagger": "2.0",
        "info": {
            "title": app.config.get("Classes Service API", "API"),
            "version": app.config.get("API_VERSION", "v1"),
            "description": app.config.get("API_DESCRIPTION", "Swagger de la API"),
        },
        "securityDefinitions": {
            "bearerAuth": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header. Ejemplo: Bearer <token>"
            }
        },
    }

    config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "openapi",
                "route": "/openapi.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs/swagger/",
    }

    Swagger(app, template=template, config=config)