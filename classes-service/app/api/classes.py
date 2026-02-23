from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from app.infraestructure.db import SessionLocal
from app.infraestructure.repositories import create_class, list_classes, get_class, has_classes
from app.domain.schemas import ClassCreate, ClassRead
from app.infraestructure.trainers_client import (
    ensure_trainer_exists,
    list_trainers,
    TrainerNotFound,
    TrainersUnavailable,
)

bp = Blueprint("classes", __name__, url_prefix="/classes")


@bp.post("")
def create():
    db = SessionLocal()
    try:
        data = request.get_json(silent=True) or {}
        payload = ClassCreate.model_validate(data)

        # Validación REST contra trainers-service
        try:
            ensure_trainer_exists(payload.trainer_id)
        except TrainerNotFound:
            return jsonify({"error": "trainer_not_found", "trainer_id": payload.trainer_id}), 400
        except TrainersUnavailable:
            return jsonify({"error": "trainers_unavailable"}), 503

        c = create_class(db, payload)

        out = ClassRead(
            id=c.id,
            name=c.name,
            schedule=c.schedule,
            max_capacity=c.max_capacity,
            trainer_id=c.trainer_id,
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
        classes = list_classes(db)
        out = [
            ClassRead(
                id=c.id,
                name=c.name,
                schedule=c.schedule,
                max_capacity=c.max_capacity,
                trainer_id=c.trainer_id,
            ).model_dump()
            for c in classes
        ]
        return jsonify(out), 200
    finally:
        db.close()


@bp.get("/<int:class_id>")
def get_one(class_id: int):
    db = SessionLocal()
    try:
        c = get_class(db, class_id)
        if not c:
            return jsonify({"error": "class_not_found", "class_id": class_id}), 404

        out = ClassRead(
            id=c.id,
            name=c.name,
            schedule=c.schedule,
            max_capacity=c.max_capacity,
            trainer_id=c.trainer_id,
        )
        return jsonify(out.model_dump()), 200
    finally:
        db.close()


@bp.post("/seed")
def seed():
    """
    Replica la idea del DataLoader del monolito.
    Idempotente: si ya hay clases, responde "already_seeded".
    """
    db = SessionLocal()
    try:
        if has_classes(db):
            return jsonify({"status": "already_seeded"}), 200

        # Traer entrenadores disponibles desde trainers-service
        try:
            trainers = list_trainers()
        except TrainersUnavailable:
            return jsonify({"error": "trainers_unavailable"}), 503

        trainer_ids = [t.get("id") for t in trainers if isinstance(t, dict) and t.get("id")]
        if len(trainer_ids) < 2:
            return jsonify({"error": "not_enough_trainers_to_seed"}), 400

        samples = [
            ClassCreate(name="Yoga Matutino", schedule="Lunes 8am", max_capacity=20, trainer_id=trainer_ids[0]),
            ClassCreate(name="Crossfit", schedule="Martes 6pm", max_capacity=15, trainer_id=trainer_ids[1]),
        ]

        created = []
        for s in samples:
            # Doble validación (por seguridad)
            ensure_trainer_exists(s.trainer_id)
            c = create_class(db, s)
            created.append(
                ClassRead(
                    id=c.id,
                    name=c.name,
                    schedule=c.schedule,
                    max_capacity=c.max_capacity,
                    trainer_id=c.trainer_id,
                ).model_dump()
            )

        return jsonify({"status": "seeded", "created": created}), 201

    except TrainerNotFound:
        # En caso raro de inconsistencia entre list_trainers y ensure_trainer_exists
        return jsonify({"error": "trainer_not_found_during_seed"}), 400
    except TrainersUnavailable:
        return jsonify({"error": "trainers_unavailable"}), 503
    finally:
        db.close()