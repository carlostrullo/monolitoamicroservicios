from flask import Blueprint, request, jsonify
from pydantic import ValidationError

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
def create():
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
def list_all():
    db = SessionLocal()
    try:
        items = list_equipment(db)
        out = [
            EquipmentRead(id=i.id, name=i.name, description=i.description, quantity=i.quantity).model_dump()
            for i in items
        ]
        return jsonify(out), 200
    finally:
        db.close()


@bp.get("/<int:equipment_id>")
def get_one(equipment_id: int):
    db = SessionLocal()
    try:
        item = get_equipment(db, equipment_id)
        if not item:
            return jsonify({"error": "equipment_not_found"}), 404
        out = EquipmentRead(id=item.id, name=item.name, description=item.description, quantity=item.quantity)
        return jsonify(out.model_dump()), 200
    finally:
        db.close()


@bp.post("/seed")
def seed():
    """
    Replica la idea del DataLoader del monolito: cargar equipos de ejemplo.
    Decisión: idempotente => si ya hay equipos, no vuelve a sembrar.
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