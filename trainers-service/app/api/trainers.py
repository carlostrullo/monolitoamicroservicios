from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from app.auth.keycloak import requires_roles
from app.infraestructure.db import SessionLocal
from app.infraestructure.repositories import create_trainer, list_trainers, get_trainer, has_trainers
from app.domain.schemas import TrainerCreate, TrainerRead

bp = Blueprint("trainers", __name__, url_prefix="/trainers")


@bp.post("")
@requires_roles("ROLE_TRAINERS_WRITE")
def create():
    """
    Crear entrenador
    ---
    tags:
      - Trainers
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
            - specialty
          properties:
            name:
              type: string
              example: Andres Mora
            specialty:
              type: string
              example: Funcional
    responses:
      201:
        description: Entrenador creado correctamente
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
@requires_roles("ROLE_TRAINERS_READ")
def list_all():
    """
    Listar entrenadores
    ---
    tags:
      - Trainers
    security:
      - bearerAuth: []
    produces:
      - application/json
    responses:
      200:
        description: Lista de entrenadores
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
    """
    db = SessionLocal()
    try:
        trainers = list_trainers(db)
        out = [TrainerRead(id=t.id, name=t.name, specialty=t.specialty).model_dump() for t in trainers]
        return jsonify(out), 200
    finally:
        db.close()


@bp.get("/<int:trainer_id>")
@requires_roles("ROLE_TRAINERS_READ")
def get_one(trainer_id: int):
    """
    Obtener entrenador por ID
    ---
    tags:
      - Trainers
    security:
      - bearerAuth: []
    produces:
      - application/json
    parameters:
      - in: path
        name: trainer_id
        type: integer
        required: true
        example: 1
    responses:
      200:
        description: Entrenador encontrado
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
      404:
        description: Entrenador no encontrado
    """
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
@requires_roles("ROLE_TRAINERS_WRITE")
def seed():
    """
    Sembrar entrenadores de ejemplo
    ---
    tags:
      - Trainers
    security:
      - bearerAuth: []
    produces:
      - application/json
    responses:
      200:
        description: Ya existían entrenadores de ejemplo
      201:
        description: Entrenadores sembrados correctamente
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
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