from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from app.infraestructure.db import SessionLocal
from app.infraestructure.repositories import create_trainer, list_trainers, get_trainer, has_trainers
from app.domain.schemas import TrainerCreate, TrainerRead

bp = Blueprint("trainers", __name__, url_prefix="/trainers")


@bp.post("")
def create():
    db = SessionLocal()
    try:
        data = request.get_json(silent=True) or {}
        payload = TrainerCreate.model_validate(data)
        trainer = create_trainer(db, payload)
        out = TrainerRead(id=trainer.id, name=trainer.name, specialty=trainer.specialty)
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
        trainers = list_trainers(db)
        out = [TrainerRead(id=t.id, name=t.name, specialty=t.specialty).model_dump() for t in trainers]
        return jsonify(out), 200
    finally:
        db.close()


@bp.get("/<int:trainer_id>")
def get_one(trainer_id: int):
    db = SessionLocal()
    try:
        trainer = get_trainer(db, trainer_id)
        if not trainer:
            return jsonify({"error": "trainer_not_found"}), 404
        out = TrainerRead(id=trainer.id, name=trainer.name, specialty=trainer.specialty)
        return jsonify(out.model_dump()), 200
    finally:
        db.close()


@bp.post("/seed")
def seed():
    """
    Replica la idea del DataLoader del monolito: cargar entrenadores de ejemplo.
    Decisión: idempotente => si ya hay entrenadores, no vuelve a sembrar.
    """
    db = SessionLocal()
    try:
        if has_trainers(db):
            return jsonify({"status": "already_seeded"}), 200

        samples = [
            TrainerCreate(name="Carlos Rodríguez", specialty="Yoga"),
            TrainerCreate(name="Laura Martínez", specialty="Spinning"),
        ]

        created = []
        for s in samples:
            t = create_trainer(db, s)
            created.append(TrainerRead(id=t.id, name=t.name, specialty=t.specialty).model_dump())

        return jsonify({"status": "seeded", "created": created}), 201
    finally:
        db.close()