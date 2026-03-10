from flask import Blueprint, request, jsonify, current_app
from pydantic import ValidationError

from app.auth.keycloak import requires_roles
from app.infraestructure.db import SessionLocal
from app.infraestructure.repositories import create_class, list_classes, get_class, has_classes
from app.domain.schemas import ClassCreate, ClassRead
from app.infraestructure.trainers_client import (
    ensure_trainer_exists,
    list_trainers,
    TrainerNotFound,
    TrainersUnavailable,
)
from app.infraestructure.rabbitmq_publisher import publish_notification

bp = Blueprint("classes", __name__, url_prefix="/classes")


@bp.post("")
@requires_roles("ROLE_CLASSES_WRITE")
def create():
    """
    Crear clase
    ---
    tags:
      - Classes
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
            - schedule
            - max_capacity
            - trainer_id
          properties:
            name:
              type: string
              example: Pilates
            schedule:
              type: string
              example: Miercoles 7am
            max_capacity:
              type: integer
              example: 18
            trainer_id:
              type: integer
              example: 1
    responses:
      201:
        description: Clase creada correctamente
      400:
        description: Error de negocio o entrenador no encontrado
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
      422:
        description: Error de validación
      503:
        description: trainers-service no disponible
    """
    db = SessionLocal()
    try:
        data = request.get_json(silent=True) or {}
        payload = ClassCreate.model_validate(data)

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

        try:
            publish_notification(
                usuario_id=str(c.trainer_id),
                mensaje=f"📣 Se te asignó la clase '{c.name}' (ID: {c.id}) - {c.schedule}"
            )
        except Exception as e:
            current_app.logger.warning(f"RabbitMQ publish failed (create class): {e}")

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
@requires_roles("ROLE_CLASSES_READ")
def list_all():
    """
    Listar clases
    ---
    tags:
      - Classes
    security:
      - bearerAuth: []
    produces:
      - application/json
    responses:
      200:
        description: Lista de clases
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
    """
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
@requires_roles("ROLE_CLASSES_READ")
def get_one(class_id: int):
    """
    Obtener clase por ID
    ---
    tags:
      - Classes
    security:
      - bearerAuth: []
    produces:
      - application/json
    parameters:
      - in: path
        name: class_id
        type: integer
        required: true
        example: 1
    responses:
      200:
        description: Clase encontrada
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
      404:
        description: Clase no encontrada
    """
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
@requires_roles("ROLE_CLASSES_WRITE")
def seed():
    """
    Sembrar clases de ejemplo
    ---
    tags:
      - Classes
    security:
      - bearerAuth: []
    produces:
      - application/json
    responses:
      200:
        description: Ya existían clases de ejemplo
      201:
        description: Clases sembradas correctamente
      400:
        description: No hay suficientes entrenadores para sembrar
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
      503:
        description: trainers-service no disponible
    """
    db = SessionLocal()
    try:
        if has_classes(db):
            return jsonify({"status": "already_seeded"}), 200

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

            try:
                publish_notification(
                    usuario_id=str(c.trainer_id),
                    mensaje=f"📣 (Seed) Se te asignó la clase '{c.name}' (ID: {c.id}) - {c.schedule}"
                )
            except Exception as e:
                current_app.logger.warning(f"RabbitMQ publish failed (seed class {c.id}): {e}")

        return jsonify({"status": "seeded", "created": created}), 201

    except TrainerNotFound:
        return jsonify({"error": "trainer_not_found_during_seed"}), 400
    except TrainersUnavailable:
        return jsonify({"error": "trainers_unavailable"}), 503
    finally:
        db.close()