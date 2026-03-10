from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from datetime import date

from app.auth.keycloak import requires_roles
from app.infraestructure.db import SessionLocal
from app.infraestructure.repositories import (
    create_member,
    list_members,
    get_member,
    has_members,
)
from app.domain.schemas import MemberCreate, MemberRead

bp = Blueprint("members", __name__, url_prefix="/members")


@bp.post("")
@requires_roles("ROLE_MEMBERS_WRITE")
def create():
    """
    Crear miembro
    ---
    tags:
      - Members
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
            - email
            - join_date
          properties:
            name:
              type: string
              example: Carlos Ruiz
            email:
              type: string
              example: carlos.ruiz@email.com
            join_date:
              type: string
              format: date
              example: 2024-03-01
    responses:
      201:
        description: Miembro creado correctamente
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
        payload = MemberCreate.model_validate(data)

        member = create_member(db, payload)

        out = MemberRead(
            id=member.id,
            name=member.name,
            email=member.email,
            join_date=member.join_date,
        )
        return jsonify(out.model_dump(mode="json")), 201

    except ValidationError as ve:
        db.rollback()
        return jsonify({"error": "validation_error", "details": ve.errors()}), 422

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        db.close()


@bp.get("")
@requires_roles("ROLE_MEMBERS_READ")
def list_all():
    """
    Listar miembros
    ---
    tags:
      - Members
    security:
      - bearerAuth: []
    produces:
      - application/json
    responses:
      200:
        description: Lista de miembros
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
    """
    db = SessionLocal()
    try:
        members = list_members(db)
        out = [
            MemberRead(
                id=m.id,
                name=m.name,
                email=m.email,
                join_date=m.join_date
            ).model_dump(mode="json")
            for m in members
        ]
        return jsonify(out), 200
    finally:
        db.close()


@bp.get("/<int:member_id>")
@requires_roles("ROLE_MEMBERS_READ")
def get_one(member_id: int):
    """
    Obtener miembro por ID
    ---
    tags:
      - Members
    security:
      - bearerAuth: []
    produces:
      - application/json
    parameters:
      - in: path
        name: member_id
        type: integer
        required: true
        example: 1
    responses:
      200:
        description: Miembro encontrado
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
      404:
        description: Miembro no encontrado
    """
    db = SessionLocal()
    try:
        m = get_member(db, member_id)
        if not m:
            return jsonify({"error": "member_not_found", "member_id": member_id}), 404

        out = MemberRead(
            id=m.id,
            name=m.name,
            email=m.email,
            join_date=m.join_date
        )
        return jsonify(out.model_dump(mode="json")), 200
    finally:
        db.close()


@bp.post("/seed")
@requires_roles("ROLE_MEMBERS_WRITE")
def seed():
    """
    Sembrar miembros de ejemplo
    ---
    tags:
      - Members
    security:
      - bearerAuth: []
    produces:
      - application/json
    responses:
      200:
        description: Ya existían miembros de ejemplo
      201:
        description: Miembros sembrados correctamente
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
    """
    db = SessionLocal()
    try:
        if has_members(db):
            return jsonify({"status": "already_seeded"}), 200

        samples = [
            MemberCreate(name="Juan Pérez", email="juan.perez@email.com", join_date=date(2024, 1, 15)),
            MemberCreate(name="María Gómez", email="maria.gomez@email.com", join_date=date(2024, 2, 10)),
        ]

        created = []
        for s in samples:
            m = create_member(db, s)
            created.append(
                MemberRead(
                    id=m.id,
                    name=m.name,
                    email=m.email,
                    join_date=m.join_date
                ).model_dump(mode="json")
            )

        return jsonify({"status": "seeded", "created": created}), 201
    finally:
        db.close()