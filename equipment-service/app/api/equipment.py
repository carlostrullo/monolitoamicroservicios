from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from app.auth.keycloak import requires_roles
from app.infraestructure.db import SessionLocal
from app.infraestructure.repositories import (
    create_equipment,
    list_equipment,
    get_equipment,
    has_equipment,
)
from app.domain.schemas import EquipmentCreate, EquipmentRead

bp = Blueprint("equipment", __name__, url_prefix="/equipment")


@bp.post("")
@requires_roles("ROLE_EQUIPMENT_WRITE")
def create():
    """
    Crear equipo
    ---
    tags:
      - Equipment
    security:
      - bearerAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
            - description
            - quantity
          properties:
            name:
              type: string
              example: Bandas elasticas
            description:
              type: string
              example: Kit de resistencia
            quantity:
              type: integer
              example: 12
    responses:
      201:
        description: Equipo creado correctamente
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
      422:
        description: Error de validación
    """
    db = SessionLocal()
    try:
        data = request.get_json(silent=True) or {}
        payload = EquipmentCreate.model_validate(data)

        item = create_equipment(db, payload)

        out = EquipmentRead(
            id=item.id,
            name=item.name,
            description=item.description,
            quantity=item.quantity,
        )
        return jsonify(out.model_dump()), 201

    except ValidationError as ve:
        db.rollback()
        return jsonify({"error": "validation_error", "details": ve.errors()}), 422
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()


@bp.get("")
@requires_roles("ROLE_EQUIPMENT_READ")
def list_all():
    """
    Listar equipos
    ---
    tags:
      - Equipment
    security:
      - bearerAuth: []
    produces:
      - application/json
    responses:
      200:
        description: Lista de equipos
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
    """
    db = SessionLocal()
    try:
        items = list_equipment(db)
        out = [
            EquipmentRead(
                id=i.id,
                name=i.name,
                description=i.description,
                quantity=i.quantity,
            ).model_dump()
            for i in items
        ]
        return jsonify(out), 200
    finally:
        db.close()


@bp.get("/<int:equipment_id>")
@requires_roles("ROLE_EQUIPMENT_READ")
def get_one(equipment_id: int):
    """
    Obtener equipo por ID
    ---
    tags:
      - Equipment
    security:
      - bearerAuth: []
    produces:
      - application/json
    parameters:
      - in: path
        name: equipment_id
        type: integer
        required: true
        example: 1
    responses:
      200:
        description: Equipo encontrado
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
      404:
        description: Equipo no encontrado
    """
    db = SessionLocal()
    try:
        item = get_equipment(db, equipment_id)
        if not item:
            return jsonify({"error": "equipment_not_found"}), 404

        out = EquipmentRead(
            id=item.id,
            name=item.name,
            description=item.description,
            quantity=item.quantity,
        )
        return jsonify(out.model_dump()), 200
    finally:
        db.close()


@bp.post("/seed")
@requires_roles("ROLE_EQUIPMENT_WRITE")
def seed():
    """
    Sembrar equipos de ejemplo
    ---
    tags:
      - Equipment
    security:
      - bearerAuth: []
    produces:
      - application/json
    responses:
      200:
        description: Ya existían equipos de ejemplo
      201:
        description: Equipos sembrados correctamente
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
    """
    db = SessionLocal()
    try:
        if has_equipment(db):
            return jsonify({"status": "already_seeded"}), 200

        samples = [
            EquipmentCreate(name="Mancuernas", description="Set de 5kg", quantity=20),
            EquipmentCreate(name="Bicicletas", description="Spinning bikes", quantity=10),
        ]

        created = []
        for s in samples:
            item = create_equipment(db, s)
            created.append(
                EquipmentRead(
                    id=item.id,
                    name=item.name,
                    description=item.description,
                    quantity=item.quantity,
                ).model_dump()
            )

        return jsonify({"status": "seeded", "created": created}), 201
    finally:
        db.close()