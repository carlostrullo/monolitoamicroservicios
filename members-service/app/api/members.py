from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from datetime import date

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
def create():
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
def list_all():
    db = SessionLocal()
    try:
        members = list_members(db)
        out = [
            MemberRead(id=m.id, name=m.name, email=m.email, join_date=m.join_date).model_dump(mode="json")
            for m in members
        ]
        return jsonify(out), 200
    finally:
        db.close()


@bp.get("/<int:member_id>")
def get_one(member_id: int):
    db = SessionLocal()
    try:
        m = get_member(db, member_id)
        if not m:
            return jsonify({"error": "member_not_found", "member_id": member_id}), 404

        out = MemberRead(id=m.id, name=m.name, email=m.email, join_date=m.join_date)
        return jsonify(out.model_dump(mode="json")), 200
    finally:
        db.close()


@bp.post("/seed")
def seed():
    """
    Replica la idea del DataLoader del monolito: cargar datos de ejemplo.
    Decisión: idempotente => si ya hay miembros, no vuelve a sembrar.
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
                MemberRead(id=m.id, name=m.name, email=m.email, join_date=m.join_date).model_dump(mode="json")
            )

        return jsonify({"status": "seeded", "created": created}), 201
    finally:
        db.close()